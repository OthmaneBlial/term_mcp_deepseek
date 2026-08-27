"""JSON-RPC STDIO transport."""

from __future__ import annotations

import json
import logging
import sys
from typing import TextIO

from models.event_bus import EventBus
from term_mcp_deepseek.app import build_dispatcher
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.server import MCPServer
from tools.json_rpc import create_jsonrpc_error


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
                response = dispatcher.dispatch(payload)
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
