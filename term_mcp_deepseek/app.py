"""Single fail-closed Flask application factory."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from collections.abc import Mapping
from threading import Lock
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from api.routes import bp as api_bp
from models.event_bus import EventBus
from term_mcp_deepseek import __version__
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.execution import ExecutionError
from term_mcp_deepseek.server import MCPServer
from tools.auth import BearerTokenAuth
from tools.json_rpc import JSONRPCError, JSONRPCServer


class RequestLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            entries = self.requests[key]
            while entries and entries[0] <= now - self.window_seconds:
                entries.popleft()
            if len(entries) >= self.limit:
                return False
            entries.append(now)
            return True


def build_dispatcher(mcp: MCPServer) -> JSONRPCServer:
    dispatcher = JSONRPCServer()
    mcp.register_methods(dispatcher)
    return dispatcher


def create_app(
    settings: Settings | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Flask:
    selected = settings or Settings.from_env()
    validation_errors = selected.validate_for_http()
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.update(selected.as_flask_config())
    app.config["SECRET_KEY"] = hashlib.sha256(selected.auth_token.encode("utf-8")).hexdigest()
    if overrides:
        app.config.update(overrides)

    event_bus = EventBus()
    app.mcp = MCPServer(selected, event_bus)
    app.event_bus = event_bus
    app.jsonrpc = build_dispatcher(app.mcp)
    app.extensions["term_mcp"] = {
        "version": __version__,
        "settings": selected,
    }
    app.extensions["request_limiter"] = RequestLimiter(selected.rate_limit_per_minute)
    app.extensions["bearer_auth"] = BearerTokenAuth(selected.auth_token)

    app.register_blueprint(api_bp)
    if selected.trust_proxy:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.before_request
    def protect_request():
        if request.content_length and request.content_length > selected.max_request_bytes:
            return jsonify(error="request_too_large"), 413

        origin = request.headers.get("Origin")
        if origin and origin not in selected.allowed_origins:
            return jsonify(error="origin_not_allowed"), 403

        public_endpoints = {"api.health", "api.root", "static"}
        if request.endpoint in public_endpoints or request.method == "OPTIONS":
            return None

        remote_address = request.remote_addr or "unknown"
        if not app.extensions["request_limiter"].allow(remote_address):
            return jsonify(error="rate_limit_exceeded"), 429

        if not app.extensions["bearer_auth"].verify_header(
            request.headers.get("Authorization", "")
        ):
            return jsonify(error="unauthorized"), 401
        return None

    @app.after_request
    def set_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["X-MCP-Version"] = selected.mcp_version
        response.headers["Cache-Control"] = "no-store"
        origin = request.headers.get("Origin")
        if origin in selected.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @app.errorhandler(JSONRPCError)
    def handle_jsonrpc_error(error: JSONRPCError):
        payload = {
            "error": {
                "code": error.code,
                "message": error.message,
            }
        }
        if error.data is not None:
            payload["error"]["data"] = error.data
        return jsonify(payload), 400

    @app.errorhandler(ExecutionError)
    @app.errorhandler(ValueError)
    def handle_request_error(error):
        return jsonify(error="invalid_request", message=str(error)), 400

    def close_term_mcp() -> None:
        app.mcp.execution.sessions.close_all()

    app.close_term_mcp = close_term_mcp
    return app


__all__ = ["RequestLimiter", "build_dispatcher", "create_app"]
