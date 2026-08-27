"""JSON-RPC STDIO transport."""

from __future__ import annotations

import json
import logging
import sys
from typing import TextIO

from models.event_bus import EventBus
from term_mcp_deepseek.app import build_dispatcher
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.protocol import (
    modern_meta,
    stamp_modern_result,
    validate_modern_message,
)
from term_mcp_deepseek.server import MCPServer
from tools.json_rpc import JSONRPCError, create_jsonrpc_error


def serve_streams(
    reader: TextIO,
    writer: TextIO,
    error_writer: TextIO,
    settings: Settings,
) -> int:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(levelname)s %(message)s",
        stream=error_writer,
    )
    event_bus = EventBus()
    mcp = MCPServer(settings, event_bus)
    dispatcher = build_dispatcher(mcp)
    legacy_selected = False
    legacy_ready = False
    try:
        for raw_line in reader:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                response = create_jsonrpc_error(-32700, "Parse error")
            else:
                try:
                    if not isinstance(payload, dict):
                        raise JSONRPCError(-32600, "Invalid Request")
                    method = payload.get("method")
                    if modern_meta(payload) is not None:
                        validate_modern_message(payload)
                        response = stamp_modern_result(dispatcher.dispatch(payload))
                    elif method == "initialize":
                        response = dispatcher.dispatch(payload)
                        legacy_selected = bool(response and "result" in response)
                    elif legacy_selected and method == "notifications/initialized":
                        legacy_ready = True
                        response = dispatcher.dispatch(payload)
                    elif legacy_ready:
                        response = dispatcher.dispatch(payload)
                    else:
                        raise JSONRPCError(
                            -32600, "initialize must complete before legacy requests"
                        )
                except JSONRPCError as error:
                    response = create_jsonrpc_error(
                        error.code,
                        error.message,
                        payload.get("id") if isinstance(payload, dict) else None,
                        error.data,
                    )
            if response is not None:
                writer.write(json.dumps(response, separators=(",", ":")) + "\n")
                writer.flush()
    finally:
        mcp.execution.sessions.close_all()
    return 0


def run_stdio(settings: Settings | None = None) -> int:
    return serve_streams(
        sys.stdin,
        sys.stdout,
        sys.stderr,
        settings or Settings.from_env(),
    )


__all__ = ["run_stdio", "serve_streams"]
