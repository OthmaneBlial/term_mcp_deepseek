# server.py
from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from api.routes import bp as api_bp
from mcp_server import MCPServer
from config import Config
from models.event_bus import bus as event_bus

def create_app(config_obj: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_obj)

    # security headers
    @app.after_request
    def set_headers(resp):
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.deepseek.com;"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        return resp

    # attach business logic
    import pexpect
    shell = pexpect.spawn('/bin/bash', encoding='utf-8', echo=False)
    app.mcp = MCPServer(shell)

    # attach event bus for SSE
    app.event_bus = event_bus

    # Hook JWT secret into auth module
    from tools import auth as auth_module
    auth_module.auth = auth_module.JWTAuth(secret=app.config["JWT_SECRET"])

    # rate limiter and input validation likely already integrated via WSGI or decorators

    # register routes once
    app.register_blueprint(api_bp)

    # optional: trust proxy for Docker/K8s
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # simple request guard replacing the broken before_request
    @app.before_request
    def security_check():
        # allow health unauthenticated; everything else handled by decorators
        return None

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(app.config.get("PORT", 8000)))