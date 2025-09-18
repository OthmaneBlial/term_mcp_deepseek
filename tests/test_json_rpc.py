import pytest
import json
from tools.json_rpc import JSONRPCServer, JSONRPCError, create_jsonrpc_response, create_jsonrpc_error


class TestJSONRPCServer:
    """Test JSON-RPC server functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.server = JSONRPCServer()

        # Register test methods
        self.server.register_method("test.add", self._add_numbers)
        self.server.register_method("test.echo", self._echo_message)
        self.server.register_method("test.error", self._raise_error)

    def _add_numbers(self, a: int, b: int) -> int:
        """Test method to add two numbers"""
        return a + b

    def _echo_message(self, message: str) -> str:
        """Test method to echo a message"""
        return message

    def _raise_error(self):
        """Test method that raises an error"""
        raise JSONRPCError(-32000, "Test error", {"details": "This is a test error"})

    def test_register_method(self):
        """Test registering methods"""
        assert "test.add" in self.server.methods
        assert "test.echo" in self.server.methods
        assert callable(self.server.methods["test.add"])

    def test_handle_request_valid(self, mocker):
        """Test handling valid JSON-RPC requests"""
        # Mock Flask request
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "jsonrpc": "2.0",
            "method": "test.add",
            "params": {"a": 5, "b": 3},
            "id": 1
        }

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["result"] == 8
        assert response["id"] == 1

    def test_handle_request_method_not_found(self, mocker):
        """Test handling unknown method"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "jsonrpc": "2.0",
            "method": "unknown.method",
            "id": 1
        }

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]
        assert response["id"] == 1

    def test_handle_request_invalid_jsonrpc_version(self, mocker):
        """Test handling invalid JSON-RPC version"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "jsonrpc": "1.0",
            "method": "test.add",
            "id": 1
        }

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32600
        assert "Invalid Request" in response["error"]["message"]

    def test_handle_request_missing_method(self, mocker):
        """Test handling request without method"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "jsonrpc": "2.0",
            "id": 1
        }

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32600
        assert "Invalid Request" in response["error"]["message"]

    def test_handle_request_with_error_method(self, mocker):
        """Test handling method that raises an error"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "jsonrpc": "2.0",
            "method": "test.error",
            "id": 1
        }

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32000
        assert response["error"]["message"] == "Test error"
        assert response["error"]["data"]["details"] == "This is a test error"

    def test_handle_request_not_json(self, mocker):
        """Test handling non-JSON request"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = False

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32700
        assert "Parse error" in response["error"]["message"]

    def test_handle_request_json_decode_error(self, mocker):
        """Test handling JSON decode error"""
        mock_request = mocker.patch('tools.json_rpc.request')
        mock_request.is_json = True
        mock_request.get_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        response = self.server.handle_request()

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32700
        assert "Parse error" in response["error"]["message"]

    def test_create_jsonrpc_response(self):
        """Test creating JSON-RPC success response"""
        response = create_jsonrpc_response(42, 1)

        assert response["jsonrpc"] == "2.0"
        assert response["result"] == 42
        assert response["id"] == 1

    def test_create_jsonrpc_error(self):
        """Test creating JSON-RPC error response"""
        response = create_jsonrpc_error(-32601, "Method not found", 1, {"method": "unknown"})

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Method not found"
        assert response["error"]["data"]["method"] == "unknown"
        assert response["id"] == 1

    def test_create_jsonrpc_error_without_data(self):
        """Test creating JSON-RPC error response without data"""
        response = create_jsonrpc_error(-32601, "Method not found", 1)

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Method not found"
        assert "data" not in response["error"]
        assert response["id"] == 1