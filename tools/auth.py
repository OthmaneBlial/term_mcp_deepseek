# auth.py
import time
import secrets
import typing as t
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, current_app, jsonify, abort, g
import jwt  # PyJWT

# In-memory storage for tokens and clients
TOKENS = {}
CLIENTS = {
    "mcp_client": {
        "client_secret": "mcp_secret",
        "scopes": ["read", "write"]
    }
}

class JWTAuth:
    def __init__(self, secret: str, issuer: str = "term-mcp", audience: str = "term-mcp-clients"):
        self.secret = secret
        self.issuer = issuer
        self.audience = audience

    def create(self, sub: str, ttl_seconds: int = 3600) -> str:
        now = int(time.time())
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": sub,
            "iat": now,
            "exp": now + ttl_seconds,
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify(self, token: str) -> dict:
        return jwt.decode(token, self.secret, algorithms=["HS256"], audience=self.audience, issuer=self.issuer)

auth = JWTAuth(secret="CHANGE_ME")  # override via Config in app factory if desired

def _extract_bearer() -> str | None:
    hdr = request.headers.get("Authorization", "")
    if hdr.startswith("Bearer "):
        return hdr[7:]
    return None

def require_token(optional: bool = False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_bearer()
            if not token:
                if optional:
                    return fn(*args, **kwargs)
                return jsonify(error="missing_bearer_token"), 401
            try:
                claims = auth.verify(token)
                request.jwt_claims = claims  # attach for handlers
            except jwt.ExpiredSignatureError:
                return jsonify(error="token_expired"), 401
            except Exception:
                return jsonify(error="invalid_token"), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def generate_token(client_id: str, scopes: list = None) -> str:
    """Generate a new access token"""
    if scopes is None:
        scopes = ["read", "write"]

    token = secrets.token_urlsafe(32)
    expires_at = time.time() + 3600  # 1 hour

    TOKENS[token] = {
        "client_id": client_id,
        "scopes": scopes,
        "expires_at": expires_at,
        "issued_at": time.time()
    }

    return token

def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate an access token"""
    if token in TOKENS:
        token_data = TOKENS[token]
        if token_data['expires_at'] > time.time():
            return token_data
    return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({
                "error": "invalid_request",
                "error_description": "Missing or invalid Authorization header"
            }), 401

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        token_data = validate_token(token)

        if not token_data:
            return jsonify({
                "error": "invalid_token",
                "error_description": "Invalid or expired token"
            }), 401

        # Store token data in Flask g object for use in the route
        g.token_data = token_data
        return f(*args, **kwargs)

    return decorated_function

def init_oauth_app(app):
    """Initialize simple OAuth2 for the Flask app"""
    # Add token endpoint
    @app.route('/oauth/token', methods=['POST'])
    def token_endpoint():
        """Simple token endpoint for client credentials flow"""
        data = request.form or request.json or {}

        grant_type = data.get('grant_type')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')

        if grant_type != 'client_credentials':
            return jsonify({
                "error": "unsupported_grant_type",
                "error_description": "Only client_credentials grant type is supported"
            }), 400

        # Validate client
        if client_id not in CLIENTS or CLIENTS[client_id]['client_secret'] != client_secret:
            return jsonify({
                "error": "invalid_client",
                "error_description": "Invalid client credentials"
            }), 401

        # Generate token
        token = generate_token(client_id, CLIENTS[client_id]['scopes'])

        return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(CLIENTS[client_id]['scopes'])
        })

    @app.route('/oauth/revoke', methods=['POST'])
    @require_auth
    def revoke_token():
        """Revoke an access token"""
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:]  # Remove 'Bearer ' prefix

        if token in TOKENS:
            del TOKENS[token]
            return jsonify({"message": "Token revoked successfully"})
        else:
            return jsonify({"error": "Token not found"}), 404

    return app