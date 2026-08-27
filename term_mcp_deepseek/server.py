"""MCP-facing business logic with safe terminal execution."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from models.event_bus import EventBus
from term_mcp_deepseek import __version__
from term_mcp_deepseek.audit import AuditLog, SecretRedactor
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.domain import ApprovalMode
from term_mcp_deepseek.execution import ExecutionError, ExecutionService
from term_mcp_deepseek.policy import CommandPolicy
from term_mcp_deepseek.validation import validate_message, validate_session_id
from tools.deepseek_client import DeepSeekClient, DeepseekError
from tools.json_rpc import JSONRPCError, JSONRPCServer

TOOL_ARGUMENTS = {
    "terminal_plan": ({"session_id", "command"}, {"cwd"}),
    "terminal_approve": ({"session_id", "plan_id"}, set()),
    "terminal_execute": ({"session_id", "plan_id"}, set()),
    "terminal_cancel": ({"session_id"}, set()),
    "terminal_receipt": ({"session_id"}, set()),
}


class MCPServer:
    def __init__(self, settings: Settings, event_bus: EventBus) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.policy = CommandPolicy(
            workspace_root=Path(settings.workspace_root),
            mode=ApprovalMode(settings.approval_mode),
            allow_network=settings.allow_network,
        )
        redactor = SecretRedactor([settings.auth_token, settings.deepseek_api_key])
        self.redactor = redactor
        audit_log = AuditLog(settings.audit_log or None, settings.auth_token, redactor)
        self.execution = ExecutionService(
            policy=self.policy,
            event_bus=event_bus,
            audit_log=audit_log,
            max_sessions=settings.max_concurrent_sessions,
            session_timeout=settings.session_timeout,
            command_timeout=settings.command_timeout,
            max_output_bytes=settings.max_output_bytes,
        )
        self.deepseek = DeepSeekClient(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
        self._conversations: dict[str, list[dict[str, str]]] = {}
        self._conversation_lock = threading.Lock()

    def register_methods(self, dispatcher: JSONRPCServer) -> None:
        dispatcher.register_method("initialize", self.initialize)
        dispatcher.register_method("ping", self.ping)
        dispatcher.register_method("sessions/create", self.create_session)
        dispatcher.register_method("sessions/close", self.close_session)
        dispatcher.register_method("tools/list", self.list_tools)
        dispatcher.register_method("tools/call", self.call_tool)
        dispatcher.register_method("prompts/list", self.list_prompts)
        dispatcher.register_method("prompts/get", self.get_prompt)
        dispatcher.register_method("resources/list", self.list_resources)
        dispatcher.register_method("resources/read", self.read_resource)
        dispatcher.register_method("roots/list", self.list_roots)

    def initialize(
        self,
        protocolVersion: str | None = None,
        capabilities: dict[str, Any] | None = None,
        clientInfo: dict[str, Any] | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        return {
            "protocolVersion": self.settings.mcp_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "prompts": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {
                "name": "term-mcp-deepseek",
                "version": __version__,
            },
            "instructions": (
                "Create a session, plan a command, approve when required, "
                "then execute and inspect the signed receipt."
            ),
        }

    @staticmethod
    def ping() -> dict[str, bool]:
        return {"ok": True}

    def create_session(self) -> dict[str, str]:
        return self.execution.create_session()

    def close_session(self, session_id: str) -> dict[str, bool]:
        self.execution.close_session(session_id)
        with self._conversation_lock:
            self._conversations.pop(session_id, None)
        return {"closed": True}

    def list_tools(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "tools": [
                {
                    "name": "terminal_plan",
                    "description": (
                        "Validate a command against the workspace policy and create "
                        "a non-executing plan."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "command": {"type": "string"},
                            "cwd": {"type": "string"},
                        },
                        "required": ["session_id", "command"],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "terminal_approve",
                    "description": "Explicitly approve a plan that requires confirmation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "plan_id": {"type": "string"},
                        },
                        "required": ["session_id", "plan_id"],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "terminal_execute",
                    "description": "Execute an allowed plan and return a signed receipt.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "plan_id": {"type": "string"},
                        },
                        "required": ["session_id", "plan_id"],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "terminal_cancel",
                    "description": "Cancel the active command for one session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "terminal_receipt",
                    "description": "Read the latest execution receipt for one session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                },
            ]
        }

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        try:
            if name in TOOL_ARGUMENTS:
                self._validate_tool_arguments(name, arguments)
            if name == "terminal_plan":
                plan = self.execution.plan(
                    session_id=arguments["session_id"],
                    command=arguments["command"],
                    cwd=arguments.get("cwd"),
                )
                return self._tool_result(plan.to_dict())
            if name == "terminal_approve":
                plan = self.execution.approve(
                    arguments["session_id"],
                    arguments["plan_id"],
                )
                return self._tool_result(plan.to_dict())
            if name == "terminal_execute":
                receipt = self.execution.execute(
                    arguments["session_id"],
                    arguments["plan_id"],
                )
                return self._tool_result(receipt.to_dict())
            if name == "terminal_cancel":
                return self._tool_result(
                    {"cancelled": self.execution.cancel(arguments["session_id"])}
                )
            if name == "terminal_receipt":
                receipt = self.execution.latest_receipt(arguments["session_id"])
                return self._tool_result(receipt.to_dict() if receipt else {"receipt": None})
            if name in {
                "write_to_terminal",
                "read_terminal_output",
                "send_control_character",
            }:
                raise JSONRPCError(
                    -32601,
                    "Direct terminal tools were removed; use plan/approve/execute",
                )
            raise JSONRPCError(-32601, "Unknown tool", {"name": name})
        except KeyError as error:
            raise JSONRPCError(
                -32602,
                "Missing tool argument",
                {"argument": str(error)},
            ) from error
        except (ExecutionError, ValueError) as error:
            raise JSONRPCError(-32010, str(error)) from error

    def list_prompts(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "prompts": [
                {
                    "name": "safe_terminal_task",
                    "description": "Plan a terminal task without implicit execution.",
                    "arguments": [
                        {
                            "name": "task",
                            "description": "The developer task to plan",
                            "required": True,
                        }
                    ],
                }
            ]
        }

    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if name != "safe_terminal_task":
            raise JSONRPCError(-32601, "Unknown prompt", {"name": name})
        task = (arguments or {}).get("task", "")
        return {
            "description": "Plan a safe terminal task",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Propose commands for this task without executing them: {task}. "
                            "Keep every command inside the configured workspace."
                        ),
                    },
                }
            ],
        }

    def list_resources(self) -> dict[str, list[dict[str, str]]]:
        root = Path(self.settings.workspace_root)
        resources: list[dict[str, str]] = [
            {
                "uri": "workspace:///",
                "name": root.name or "workspace",
                "description": "Configured workspace root",
                "mimeType": "inode/directory",
            }
        ]
        for path in sorted(root.rglob("*")):
            if len(resources) >= 101:
                break
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(root).as_posix()
                resources.append(
                    {
                        "uri": f"workspace:///{relative}",
                        "name": relative,
                        "description": f"Workspace file: {relative}",
                        "mimeType": "text/plain",
                    }
                )
        return {"resources": resources}

    def read_resource(self, uri: str) -> dict[str, list[dict[str, str]]]:
        prefix = "workspace:///"
        if not uri.startswith(prefix):
            raise JSONRPCError(-32602, "Only workspace resources are supported")
        relative = uri[len(prefix) :]
        try:
            path = self.policy.resolve_resource(relative)
        except ValueError as error:
            raise JSONRPCError(-32011, str(error)) from error
        if not path.is_file() or path.is_symlink():
            raise JSONRPCError(-32004, "Resource is not a readable workspace file")
        if path.stat().st_size > self.settings.max_output_bytes:
            raise JSONRPCError(-32012, "Resource exceeds the configured size limit")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise JSONRPCError(-32013, "Resource is not UTF-8 text") from error
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": self.redactor.redact(text),
                }
            ]
        }

    def list_roots(self) -> dict[str, list[dict[str, str]]]:
        root = Path(self.settings.workspace_root)
        return {
            "roots": [
                {
                    "uri": "workspace:///",
                    "name": root.name or "workspace",
                }
            ]
        }

    def handle_chat(self, data: dict[str, Any]) -> dict[str, str]:
        message = validate_message(str(data.get("message", "")))
        requested_session = data.get("session_id")
        if requested_session:
            session_id = validate_session_id(str(requested_session))
            self.execution.sessions.get(session_id)
        else:
            session_id = self.execution.create_session()["session_id"]

        with self._conversation_lock:
            conversation = self._conversations.setdefault(
                session_id,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a terminal planning assistant. Never claim a command "
                            "ran and never emit hidden execution markers. Explain what should "
                            "be planned through the explicit terminal tools."
                        ),
                    }
                ],
            )
            conversation.append({"role": "user", "content": message})
            model_messages = list(conversation[-40:])

        try:
            response = self.deepseek.chat(model_messages)
        except DeepseekError as error:
            raise JSONRPCError(-32020, str(error)) from error

        with self._conversation_lock:
            self._conversations[session_id].append({"role": "assistant", "content": response})
        return {"message": response, "session_id": session_id}

    def get_info(self) -> dict[str, Any]:
        return {
            "name": "term-mcp-deepseek",
            "version": __version__,
            "description": "Safe local terminal planning and execution over MCP",
            "protocol_version": self.settings.mcp_version,
            "approval_mode": self.settings.approval_mode,
            "workspace": str(Path(self.settings.workspace_root)),
            "transports": ["http", "stdio"],
            "authentication": {"http": "bearer", "stdio": "process-local"},
        }

    @staticmethod
    def _tool_result(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(value, indent=2, sort_keys=True),
                }
            ],
            "structuredContent": value,
            "isError": False,
        }

    @staticmethod
    def _validate_tool_arguments(name: str, arguments: Any) -> None:
        if not isinstance(arguments, dict):
            raise JSONRPCError(-32602, "Tool arguments must be an object")
        required, optional = TOOL_ARGUMENTS[name]
        supplied = set(arguments)
        missing = sorted(required - supplied)
        unexpected = sorted(supplied - required - optional)
        if missing:
            raise JSONRPCError(-32602, "Missing tool arguments", {"missing": missing})
        if unexpected:
            raise JSONRPCError(-32602, "Unexpected tool arguments", {"unexpected": unexpected})
        invalid = sorted(
            key
            for key in supplied
            if not isinstance(arguments[key], str) or not arguments[key].strip()
        )
        if invalid:
            raise JSONRPCError(
                -32602,
                "Tool arguments must be non-empty strings",
                {"invalid": invalid},
            )


__all__ = ["MCPServer"]
