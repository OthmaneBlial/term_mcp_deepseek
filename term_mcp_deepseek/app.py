"""Single Flask application factory."""

from __future__ import annotations

import atexit
from collections.abc import Mapping
from typing import Any

import pexpect
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from api.routes import bp as api_bp
from mcp_server import MCPServer
from models.event_bus import EventBus
from term_mcp_deepseek import __version__
from term_mcp_deepseek.config import Settings
from tools.json_rpc import JSONRPCServer


def build_dispatcher(mcp: MCPServer) -> JSONRPCServer:
    dispatcher = JSONRPCServer()
    mcp.register_methods(dispatcher)
    return dispatcher


def create_app(
    settings: Settings | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Flask:
    selected = settings or Settings.from_env()
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.update(selected.as_flask_config())
    if overrides:
        app.config.update(overrides)

    shell = pexpect.spawn("/bin/bash", encoding="utf-8", echo=False)
    app.mcp = MCPServer(shell)
    app.event_bus = EventBus()
    app.jsonrpc = build_dispatcher(app.mcp)
    app.extensions["term_mcp"] = {
        "version": __version__,
        "settings": selected,
        "shell": shell,
    }

    app.register_blueprint(api_bp)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.after_request
    def set_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-MCP-Version", selected.mcp_version)
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    def close_shell() -> None:
        if shell.isalive():
            shell.close(force=True)

    app.close_term_mcp = close_shell
    atexit.register(close_shell)
    return app


__all__ = ["build_dispatcher", "create_app"]
