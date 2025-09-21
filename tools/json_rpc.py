import json
import uuid
from typing import Dict, Any, Optional
from flask import request, jsonify

class JSONRPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

class JSONRPCServer:
    def __init__(self):
        self.methods: Dict[str, callable] = {}

    def register_method(self, name: str, method: callable):
        """Register a method that can be called via JSON-RPC"""
        self.methods[name] = method

    def handle_request(self) -> Dict[str, Any]:
        """
        Handle a JSON-RPC request and return the response
        """
        try:
            if not request.is_json:
                raise JSONRPCError(-32700, "Parse error")

            rpc_request = request.get_json()

            # Validate JSON-RPC 2.0 format
            if not isinstance(rpc_request, dict):
                raise JSONRPCError(-32600, "Invalid Request")

            jsonrpc_version = rpc_request.get("jsonrpc")
            if jsonrpc_version != "2.0":
                raise JSONRPCError(-32600, "Invalid Request")

            method_name = rpc_request.get("method")
            if not isinstance(method_name, str):
                raise JSONRPCError(-32600, "Invalid Request")

            params = rpc_request.get("params", {})
            request_id = rpc_request.get("id")

            # Check if method exists
            if method_name not in self.methods:
                raise JSONRPCError(-32601, "Method not found")

            # Call the method
            method = self.methods[method_name]
            if isinstance(params, dict):
                result = method(**params)
            elif isinstance(params, list):
                result = method(*params)
            else:
                result = method()

            # Return success response
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        except JSONRPCError as e:
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": e.code,
                    "message": e.message
                },
                "id": request_id if 'request_id' in locals() else None
            }
            if e.data is not None:
                response["error"]["data"] = e.data

        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": request_id if 'request_id' in locals() else None
            }

        return response

def create_jsonrpc_response(result: Any, request_id: Any = None) -> Dict[str, Any]:
    """Helper to create a JSON-RPC success response"""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }

def create_jsonrpc_error(code: int, message: str, request_id: Any = None, data: Any = None) -> Dict[str, Any]:
    """Helper to create a JSON-RPC error response"""
    error = {
        "code": code,
        "message": message
    }
    if data is not None:
        error["data"] = data

    return {
        "jsonrpc": "2.0",
        "error": error,
        "id": request_id
    }