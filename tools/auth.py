"""Fail-closed HTTP bearer authentication."""

from __future__ import annotations

import secrets
import time
from functools import wraps
from typing import Any

import jwt
from flask import current_app, jsonify, request


class BearerTokenAuth:
    def __init__(self, expected_token: str) -> None:
        if len(expected_token) < 32:
            raise ValueError("bearer token must contain at least 32 characters")
        self.expected_token = expected_token

    @staticmethod
    def extract(header: str) -> str | None:
        scheme, separator, value = header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not value:
            return None
        return value

    def verify_header(self, header: str) -> bool:
        provided = self.extract(header)
        return bool(provided) and secrets.compare_digest(provided, self.expected_token)


class JWTAuth:
    """Compatibility helper for clients that issue their own short-lived JWT."""

    def __init__(
        self,
        secret: str,
        issuer: str = "term-mcp",
        audience: str = "term-mcp-clients",
    ) -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must contain at least 32 characters")
        self.secret = secret
        self.issuer = issuer
        self.audience = audience

    def create(self, sub: str, ttl_seconds: int = 3600) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self.issuer,
                "aud": self.audience,
                "sub": sub,
                "iat": now,
                "exp": now + ttl_seconds,
            },
            self.secret,
            algorithm="HS256",
        )

    def verify(self, token: str) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.secret,
            algorithms=["HS256"],
            audience=self.audience,
            issuer=self.issuer,
        )


def require_token(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        auth = BearerTokenAuth(current_app.config["AUTH_TOKEN"])
        if not auth.verify_header(request.headers.get("Authorization", "")):
            return jsonify(error="unauthorized"), 401
        return function(*args, **kwargs)

    return wrapper


__all__ = ["BearerTokenAuth", "JWTAuth", "require_token"]
