"""Dual-era MCP protocol validation shared by HTTP and STDIO transports."""

from __future__ import annotations

import base64
import binascii
import time
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from term_mcp_deepseek import __version__
from tools.json_rpc import JSONRPCError

MODERN_PROTOCOL_VERSION = "2026-07-28"
LEGACY_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = (MODERN_PROTOCOL_VERSION, LEGACY_PROTOCOL_VERSION)

PROTOCOL_VERSION_META = "io.modelcontextprotocol/protocolVersion"
CLIENT_INFO_META = "io.modelcontextprotocol/clientInfo"
CLIENT_CAPABILITIES_META = "io.modelcontextprotocol/clientCapabilities"
SERVER_INFO_META = "io.modelcontextprotocol/serverInfo"

NAMED_METHODS = {"tools/call": "name", "resources/read": "uri", "prompts/get": "name"}


@dataclass(frozen=True)
class ProtocolContext:
    era: str
    version: str
    initialize: bool = False
    transport_session_id: str | None = None

    @property
    def modern(self) -> bool:
        return self.era == "modern"


@dataclass
class LegacyHTTPSession:
    id: str
    protocol_version: str
    last_activity: float


class LegacyHTTPSessions:
    def __init__(self, timeout_seconds: int = 3600, max_sessions: int = 100) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, LegacyHTTPSession] = {}
        self._lock = Lock()

    def create(self, protocol_version: str) -> LegacyHTTPSession:
        with self._lock:
            self._cleanup_locked()
            if len(self._sessions) >= self.max_sessions:
                raise JSONRPCError(
                    -32000, "Maximum MCP transport sessions reached", http_status=503
                )
            session = LegacyHTTPSession(str(uuid4()), protocol_version, time.time())
            self._sessions[session.id] = session
            return session

    def get(self, session_id: str) -> LegacyHTTPSession:
        with self._lock:
            self._cleanup_locked()
            session = self._sessions.get(session_id)
            if session is None:
                raise JSONRPCError(-32600, "Missing or invalid Mcp-Session-Id")
            session.last_activity = time.time()
            return session

    def close(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def _cleanup_locked(self) -> None:
        cutoff = time.time() - self.timeout_seconds
        expired = [key for key, value in self._sessions.items() if value.last_activity < cutoff]
        for key in expired:
            self._sessions.pop(key, None)


def modern_meta(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    params = payload.get("params")
    if not isinstance(params, Mapping):
        return None
    meta = params.get("_meta")
    if not isinstance(meta, Mapping):
        return None
    if PROTOCOL_VERSION_META not in meta:
        return None
    return meta


def validate_modern_message(payload: Mapping[str, Any]) -> str:
    meta = modern_meta(payload)
    if meta is None:
        raise JSONRPCError(-32602, "Modern MCP requests require per-request _meta")
    version = meta.get(PROTOCOL_VERSION_META)
    if version not in SUPPORTED_PROTOCOL_VERSIONS:
        raise JSONRPCError(
            -32022,
            "Unsupported protocol version",
            {"supported": list(SUPPORTED_PROTOCOL_VERSIONS), "requested": version},
        )
    if version != MODERN_PROTOCOL_VERSION:
        raise JSONRPCError(
            -32022,
            "Legacy protocol versions require initialize",
            {"supported": list(SUPPORTED_PROTOCOL_VERSIONS), "requested": version},
        )
    capabilities = meta.get(CLIENT_CAPABILITIES_META)
    if not isinstance(capabilities, Mapping):
        raise JSONRPCError(-32602, "Modern MCP requests require clientCapabilities metadata")
    client_info = meta.get(CLIENT_INFO_META)
    if client_info is not None and not isinstance(client_info, Mapping):
        raise JSONRPCError(-32602, "clientInfo metadata must be an object")
    return version


def validate_http_request(
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    sessions: LegacyHTTPSessions,
) -> ProtocolContext:
    method = payload.get("method")
    if not isinstance(method, str) or not method:
        raise JSONRPCError(-32600, "Invalid Request")

    meta = modern_meta(payload)
    if meta is not None:
        version = validate_modern_message(payload)
        _require_accept(headers)
        _match_header(headers, "MCP-Protocol-Version", version)
        _match_header(headers, "Mcp-Method", method)
        name_source = NAMED_METHODS.get(method)
        if name_source:
            params = payload.get("params")
            expected_name = params.get(name_source) if isinstance(params, Mapping) else None
            if not isinstance(expected_name, str):
                raise JSONRPCError(-32602, f"{method} requires params.{name_source}")
            _match_header(headers, "Mcp-Name", expected_name, encoded=True)
        return ProtocolContext("modern", version)

    if method == "initialize":
        _require_accept(headers)
        return ProtocolContext("legacy", LEGACY_PROTOCOL_VERSION, initialize=True)

    session_id = headers.get("Mcp-Session-Id", "")
    session = sessions.get(session_id)
    _require_accept(headers)
    _match_header(headers, "MCP-Protocol-Version", session.protocol_version)
    return ProtocolContext(
        "legacy",
        session.protocol_version,
        transport_session_id=session.id,
    )


def stamp_modern_result(response: dict[str, Any] | None) -> dict[str, Any] | None:
    if response is None or not isinstance(response.get("result"), dict):
        return response
    result = response["result"]
    result.setdefault("resultType", "complete")
    meta = result.setdefault("_meta", {})
    if isinstance(meta, dict):
        meta.setdefault(
            SERVER_INFO_META,
            {"name": "term-mcp-deepseek", "version": __version__},
        )
    return response


def _require_accept(headers: Mapping[str, str]) -> None:
    accepted = {part.strip().split(";", 1)[0] for part in headers.get("Accept", "").split(",")}
    if not {"application/json", "text/event-stream"}.issubset(accepted):
        raise JSONRPCError(
            -32020,
            "Client must accept application/json and text/event-stream",
            http_status=406,
        )


def _match_header(
    headers: Mapping[str, str],
    name: str,
    expected: str,
    *,
    encoded: bool = False,
) -> None:
    actual = headers.get(name)
    if actual is not None and encoded:
        actual = _decode_header_value(actual)
    if actual != expected:
        raise JSONRPCError(
            -32020,
            f"Header mismatch: {name} must match the request body",
            {"header": name, "expected": expected},
        )


def _decode_header_value(value: str) -> str:
    prefix = "=?base64?"
    suffix = "?="
    if not (value.startswith(prefix) and value.endswith(suffix)):
        return value
    encoded = value[len(prefix) : -len(suffix)]
    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise JSONRPCError(-32020, "Header mismatch: invalid Base64 header value") from error


__all__ = [
    "CLIENT_CAPABILITIES_META",
    "CLIENT_INFO_META",
    "LEGACY_PROTOCOL_VERSION",
    "LegacyHTTPSessions",
    "MODERN_PROTOCOL_VERSION",
    "PROTOCOL_VERSION_META",
    "ProtocolContext",
    "SERVER_INFO_META",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "modern_meta",
    "stamp_modern_result",
    "validate_http_request",
    "validate_modern_message",
]
