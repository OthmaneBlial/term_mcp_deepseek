"""Small value validators that never decide whether a command is safe."""

from __future__ import annotations

import re

SESSION_ID = re.compile(r"^[A-Za-z0-9-]{8,128}$")


def validate_message(value: str, *, max_length: int = 10_000) -> str:
    message = value.strip()
    if not message:
        raise ValueError("message is required")
    if len(message) > max_length:
        raise ValueError(f"message cannot exceed {max_length} characters")
    return message


def validate_session_id(value: str) -> str:
    if not SESSION_ID.fullmatch(value):
        raise ValueError("session_id must be 8-128 letters, digits, or hyphens")
    return value


__all__ = ["validate_message", "validate_session_id"]
