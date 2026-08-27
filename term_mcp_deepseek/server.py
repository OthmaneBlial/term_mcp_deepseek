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
from term_mcp_deepseek.protocol import (
    LEGACY_PROTOCOL_VERSION,
    SERVER_INFO_META,
    SUPPORTED_PROTOCOL_VERSIONS,
)
from term_mcp_deepseek.validation import validate_message, validate_session_id
from tools.deepseek_client import DeepSeekClient, DeepseekError
from tools.json_rpc import JSONRPCError, JSONRPCServer

TOOL_ARGUMENTS = {
    "terminal_plan": ({"command"}, {"session_id", "cwd"}),
    "terminal_approve": ({"session_id", "plan_id"}, set()),
    "terminal_execute": ({"session_id", "plan_id"}, set()),
    "terminal_retry": ({"session_id", "plan_id"}, set()),
    "terminal_pause": ({"session_id"}, set()),
    "terminal_resume": ({"session_id"}, set()),
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
            timeout=settings.deepseek_timeout,
            max_retries=settings.deepseek_max_retries,
            backoff=settings.deepseek_backoff,
            max_tokens=settings.deepseek_max_tokens,
        )
        self._conversations: dict[str, list[dict[str, str]]] = {}
        self._conversation_lock = threading.Lock()

    def register_methods(self, dispatcher: JSONRPCServer) -> None:
        dispatcher.register_method("server/discover", self.discover)
        dispatcher.register_method("initialize", self.initialize)
        dispatcher.register_method("notifications/initialized", self.initialized)
        dispatcher.register_method("notifications/cancelled", self.cancelled)
        dispatcher.register_method("ping", self.ping)
        dispatcher.register_method("tools/list", self.list_tools)
        dispatcher.register_method("tools/call", self.call_tool)
        dispatcher.register_method("prompts/list", self.list_prompts)
        dispatcher.register_method("prompts/get", self.get_prompt)
        dispatcher.register_method("resources/list", self.list_resources)
        dispatcher.register_method("resources/read", self.read_resource)

    @staticmethod
    def capabilities() -> dict[str, Any]:
        return {
            "tools": {"listChanged": False},
            "prompts": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
        }

    def discover(self, **_params: Any) -> dict[str, Any]:
        return {
            "resultType": "complete",
            "supportedVersions": list(SUPPORTED_PROTOCOL_VERSIONS),
            "capabilities": self.capabilities(),
            "_meta": {
                SERVER_INFO_META: {
                    "name": "term-mcp-deepseek",
                    "version": __version__,
                }
            },
            "instructions": (
                "Plan terminal commands first. Execute only allowed plans and inspect "
                "the signed receipt returned by every execution."
            ),
            "ttlMs": 3_600_000,
            "cacheScope": "private",
        }

    def initialize(
        self,
        protocolVersion: str | None = None,
        capabilities: dict[str, Any] | None = None,
        clientInfo: dict[str, Any] | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        if not isinstance(protocolVersion, str):
            raise JSONRPCError(-32602, "initialize requires protocolVersion")
        if not isinstance(capabilities, dict) or not isinstance(clientInfo, dict):
            raise JSONRPCError(-32602, "initialize requires capabilities and clientInfo objects")
        return {
            "protocolVersion": LEGACY_PROTOCOL_VERSION,
            "capabilities": self.capabilities(),
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
    def initialized(**_params: Any) -> dict[str, bool]:
        return {"accepted": True}

    @staticmethod
    def cancelled(**_params: Any) -> dict[str, bool]:
        return {"accepted": True}

    @staticmethod
    def ping(**_params: Any) -> dict[str, bool]:
        return {"ok": True}

    def create_session(self) -> dict[str, str]:
        return self.execution.create_session()

    def close_session(self, session_id: str) -> dict[str, bool]:
        self.execution.close_session(session_id)
        with self._conversation_lock:
            self._conversations.pop(session_id, None)
        return {"closed": True}

    def list_tools(self, cursor: str | None = None, **_params: Any) -> dict[str, Any]:
        if cursor is not None:
            raise JSONRPCError(-32602, "This catalog has no additional page")
        return {
            "resultType": "complete",
            "tools": [
                {
                    "name": "terminal_plan",
                    "title": "Plan a bounded terminal command",
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
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": True, "destructiveHint": False},
                },
                {
                    "name": "terminal_approve",
                    "title": "Approve a terminal plan",
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
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": False, "destructiveHint": False},
                },
                {
                    "name": "terminal_execute",
                    "title": "Execute an approved terminal plan",
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
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": False, "destructiveHint": True},
                },
                {
                    "name": "terminal_retry",
                    "title": "Create a controlled retry plan",
                    "description": (
                        "Create a fresh non-executing plan from an earlier command. "
                        "The new plan must pass policy and approval again."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "plan_id": {"type": "string"},
                        },
                        "required": ["session_id", "plan_id"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": True, "destructiveHint": False},
                },
                {
                    "name": "terminal_pause",
                    "title": "Pause the active command",
                    "description": "Pause the active process group for one execution session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": False, "destructiveHint": False},
                },
                {
                    "name": "terminal_resume",
                    "title": "Resume the paused command",
                    "description": "Resume a paused process group for one execution session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": False, "destructiveHint": False},
                },
                {
                    "name": "terminal_cancel",
                    "title": "Cancel the active command",
                    "description": "Cancel the active command for one session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": False, "destructiveHint": True},
                },
                {
                    "name": "terminal_receipt",
                    "title": "Read the latest signed receipt",
                    "description": "Read the latest execution receipt for one session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    "outputSchema": {"type": "object"},
                    "annotations": {"readOnlyHint": True, "destructiveHint": False},
                },
            ],
            "ttlMs": 300_000,
            "cacheScope": "private",
        }

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        **_params: Any,
    ) -> dict[str, Any]:
        arguments = arguments or {}
        try:
            if name in TOOL_ARGUMENTS:
                self._validate_tool_arguments(name, arguments)
            if name == "terminal_plan":
                session_id = arguments.get("session_id")
                if session_id is None:
                    session_id = self.execution.create_session()["session_id"]
                plan = self.execution.plan(
                    session_id=session_id,
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
                return self._tool_result(
                    receipt.to_dict(),
                    is_error=receipt.status.value != "succeeded",
                )
            if name == "terminal_retry":
                plan = self.execution.replan(arguments["session_id"], arguments["plan_id"])
                return self._tool_result(plan.to_dict())
            if name == "terminal_pause":
                return self._tool_result({"paused": self.execution.pause(arguments["session_id"])})
            if name == "terminal_resume":
                return self._tool_result(
                    {"resumed": self.execution.resume(arguments["session_id"])}
                )
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
                    -32602,
                    "Direct terminal tools were removed; use plan/approve/execute",
                )
            raise JSONRPCError(-32602, "Unknown tool", {"name": name})
        except KeyError as error:
            raise JSONRPCError(
                -32602,
                "Missing tool argument",
                {"argument": str(error)},
            ) from error
        except (ExecutionError, ValueError) as error:
            return self._tool_error(str(error))

    def list_prompts(self, cursor: str | None = None, **_params: Any) -> dict[str, Any]:
        if cursor is not None:
            raise JSONRPCError(-32602, "This catalog has no additional page")
        return {
            "resultType": "complete",
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
            ],
        }

    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        **_params: Any,
    ) -> dict[str, Any]:
        if name != "safe_terminal_task":
            raise JSONRPCError(-32602, "Unknown prompt", {"name": name})
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

    def list_resources(self, cursor: str | None = None, **_params: Any) -> dict[str, Any]:
        if cursor is not None:
            raise JSONRPCError(-32602, "This catalog has no additional page")
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
        return {"resultType": "complete", "resources": resources}

    def read_resource(self, uri: str, **_params: Any) -> dict[str, list[dict[str, str]]]:
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
            "supported_protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
            "approval_mode": self.settings.approval_mode,
            "workspace": str(Path(self.settings.workspace_root)),
            "network_allowed": self.settings.allow_network,
            "limits": {
                "session_timeout_seconds": self.settings.session_timeout,
                "command_timeout_seconds": self.settings.command_timeout,
                "max_output_bytes": self.settings.max_output_bytes,
            },
            "transports": ["http", "stdio"],
            "authentication": {"http": "bearer", "stdio": "process-local"},
            "model": {
                "provider": "deepseek",
                "model": self.settings.deepseek_model,
                "available": self.deepseek.available,
                "timeout_seconds": self.settings.deepseek_timeout,
                "max_retries": self.settings.deepseek_max_retries,
                "max_tokens": self.settings.deepseek_max_tokens,
            },
        }

    @staticmethod
    def _tool_result(value: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
        return {
            "resultType": "complete",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(value, indent=2, sort_keys=True),
                }
            ],
            "structuredContent": value,
            "isError": is_error,
        }

    @staticmethod
    def _tool_error(message: str) -> dict[str, Any]:
        value = {"code": "tool_execution_error", "message": message}
        return {
            "resultType": "complete",
            "content": [{"type": "text", "text": message}],
            "structuredContent": value,
            "isError": True,
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
            raise ValueError(f"missing required tool arguments: {', '.join(missing)}")
        if unexpected:
            raise ValueError(f"unexpected tool arguments: {', '.join(unexpected)}")
        invalid = sorted(
            key
            for key in supplied
            if not isinstance(arguments[key], str) or not arguments[key].strip()
        )
        if invalid:
            raise ValueError(f"tool arguments must be non-empty strings: {', '.join(invalid)}")


__all__ = ["MCPServer"]
