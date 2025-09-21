import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask
from tools.auth import init_oauth_app
from api.routes import APIRoutes
from models.conversation_store import conversation_store


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    def setup_method(self):
        """Setup test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret'
        self.app.config['TESTING'] = True

        # Initialize OAuth
        self.app = init_oauth_app(self.app)

        # Mock shell for testing
        mock_shell = Mock()
        mock_shell.sendline = Mock()
        mock_shell.read_nonblocking = Mock(return_value=b"")

        # Initialize routes
        self.api_routes = APIRoutes(self.app, None, conversation_store)

        self.client = self.app.test_client()

    def get_auth_token(self):
        """Get authentication token for tests"""
        response = self.client.post('/oauth/token', data={
            'grant_type': 'client_credentials',
            'client_id': 'mcp_client',
            'client_secret': 'mcp_secret'
        })
        data = json.loads(response.data)
        return data['access_token']

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'term-mcp-deepseek'
        assert 'version' in data

    def test_mcp_info_endpoint(self):
        """Test MCP info endpoint"""
        response = self.client.get('/mcp/info')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['name'] == 'term-mcp-deepseek'
        assert 'capabilities' in data
        assert 'tools' in data['capabilities']
        assert 'authentication' in data

    def test_oauth_token_endpoint(self):
        """Test OAuth token endpoint"""
        response = self.client.post('/oauth/token', data={
            'grant_type': 'client_credentials',
            'client_id': 'mcp_client',
            'client_secret': 'mcp_secret'
        })
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'
        assert 'expires_in' in data

    def test_oauth_token_invalid_credentials(self):
        """Test OAuth token endpoint with invalid credentials"""
        response = self.client.post('/oauth/token', data={
            'grant_type': 'client_credentials',
            'client_id': 'invalid_client',
            'client_secret': 'invalid_secret'
        })
        assert response.status_code == 401

    @patch('api.routes.call_deepseek_api')
    def test_chat_endpoint_authenticated(self, mock_deepseek):
        """Test chat endpoint with authentication"""
        # Mock DeepSeek API response
        mock_deepseek.return_value = "Hello! How can I help you today?"

        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/chat',
            json={'message': 'Hello'},
            headers=headers
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'message' in data
        assert 'session_id' in data

    def test_chat_endpoint_unauthenticated(self):
        """Test chat endpoint without authentication"""
        response = self.client.post('/chat', json={'message': 'Hello'})
        assert response.status_code == 401

    def test_chat_endpoint_invalid_input(self):
        """Test chat endpoint with invalid input"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        # Empty message
        response = self.client.post('/chat', json={}, headers=headers)
        assert response.status_code == 400

        # No JSON
        response = self.client.post('/chat', headers=headers)
        assert response.status_code == 400

    def test_list_tools_endpoint_authenticated(self):
        """Test list tools endpoint with authentication"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/list_tools', headers=headers)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'tools' in data
        assert isinstance(data['tools'], list)
        assert len(data['tools']) > 0

        # Check tool structure
        tool = data['tools'][0]
        assert 'name' in tool
        assert 'description' in tool
        assert 'inputSchema' in tool

    def test_list_tools_endpoint_unauthenticated(self):
        """Test list tools endpoint without authentication"""
        response = self.client.post('/mcp/list_tools')
        assert response.status_code == 401

    def test_call_tool_endpoint_authenticated(self):
        """Test call tool endpoint with authentication"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/call_tool',
            json={
                'name': 'read_terminal_output',
                'arguments': {'linesOfOutput': 10}
            },
            headers=headers
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'content' in data
        assert isinstance(data['content'], list)

    def test_call_tool_endpoint_invalid_tool(self):
        """Test call tool endpoint with invalid tool name"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/call_tool',
            json={
                'name': 'invalid_tool',
                'arguments': {}
            },
            headers=headers
        )
        assert response.status_code == 200  # JSON-RPC error in response body

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == -32601

    def test_call_tool_endpoint_missing_arguments(self):
        """Test call tool endpoint with missing arguments"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/call_tool',
            json={'name': 'write_to_terminal'},
            headers=headers
        )
        assert response.status_code == 200  # JSON-RPC error in response body

        data = json.loads(response.data)
        assert 'error' in data

    def test_jsonrpc_endpoint_authenticated(self):
        """Test JSON-RPC endpoint with authentication"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/jsonrpc',
            json={
                'jsonrpc': '2.0',
                'method': 'tools/list',
                'id': 1
            },
            headers=headers
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['jsonrpc'] == '2.0'
        assert 'result' in data
        assert data['id'] == 1

    def test_jsonrpc_endpoint_invalid_request(self):
        """Test JSON-RPC endpoint with invalid request"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.post('/mcp/jsonrpc',
            json={'invalid': 'request'},
            headers=headers
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == -32600

    def test_sessions_endpoint_authenticated(self):
        """Test sessions endpoint with authentication"""
        token = self.get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.get('/sessions', headers=headers)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'sessions' in data
        assert isinstance(data['sessions'], list)

    def test_sessions_endpoint_unauthenticated(self):
        """Test sessions endpoint without authentication"""
        response = self.client.get('/sessions')
        assert response.status_code == 401

    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = self.client.get('/health')
        assert response.headers.get('Access-Control-Allow-Origin') == '*'
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers

    def test_mcp_headers(self):
        """Test MCP-specific headers are present"""
        response = self.client.get('/health')
        assert response.headers.get('X-MCP-Version') == '1.0'
        assert response.headers.get('X-MCP-Transport') == 'http'
        assert response.headers.get('Cache-Control') == 'no-cache'