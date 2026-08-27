"""Transport-independent JSON-RPC 2.0 dispatcher."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any


class JSONRPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class JSONRPCServer:
    def __init__(self) -> None:
        self.methods: dict[str, Callable[..., Any]] = {}

    def register_method(self, name: str, method: Callable[..., Any]) -> None:
        self.methods[name] = method

    def dispatch(self, payload: Any) -> dict[str, Any] | None:
        request_id: Any = None
        has_id = isinstance(payload, Mapping) and "id" in payload
        if has_id:
            request_id = payload.get("id")

        try:
            if not isinstance(payload, Mapping):
                raise JSONRPCError(-32600, "Invalid Request")
            if payload.get("jsonrpc") != "2.0":
                raise JSONRPCError(-32600, "Invalid Request")

            method_name = payload.get("method")
            if not isinstance(method_name, str) or not method_name:
                raise JSONRPCError(-32600, "Invalid Request")
            if method_name not in self.methods:
                raise JSONRPCError(-32601, "Method not found", {"method": method_name})

            params = payload.get("params", {})
            method = self.methods[method_name]
            if isinstance(params, Mapping):
                result = method(**params)
            elif isinstance(params, Sequence) and not isinstance(params, (str, bytes, bytearray)):
                result = method(*params)
            else:
                raise JSONRPCError(-32602, "Invalid params")

            if inspect.isawaitable(result):
                raise JSONRPCError(-32603, "Async methods require an async dispatcher")
            if not has_id:
                return None
            return create_jsonrpc_response(result, request_id)
        except JSONRPCError as error:
            if not has_id and isinstance(payload, Mapping):
                return None
            return create_jsonrpc_error(
                error.code,
                error.message,
                request_id,
                error.data,
            )
        except TypeError as error:
            if not has_id:
                return None
            return create_jsonrpc_error(-32602, "Invalid params", request_id, str(error))
        except Exception:
            if not has_id:
                return None
            return create_jsonrpc_error(-32603, "Internal error", request_id)

    def handle_request(self, payload: Any = None) -> dict[str, Any] | None:
        """Compatibility wrapper for legacy Flask callers and tests."""
        if payload is None:
            try:
                from flask import request

                if not request.is_json:
                    return create_jsonrpc_error(-32700, "Parse error")
                payload = request.get_json()
            except RuntimeError:
                return create_jsonrpc_error(-32700, "Parse error")
            except Exception:
                return create_jsonrpc_error(-32700, "Parse error")
        return self.dispatch(payload)


def create_jsonrpc_response(result: Any, request_id: Any = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "result": result, "id": request_id}


def create_jsonrpc_error(
    code: int,
    message: str,
    request_id: Any = None,
    data: Any = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "error": error, "id": request_id}


__all__ = [
    "JSONRPCError",
    "JSONRPCServer",
    "create_jsonrpc_error",
    "create_jsonrpc_response",
]
