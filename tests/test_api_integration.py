import pytest
import json


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    def test_health_endpoint(self, app):
        """Test health check endpoint"""
        client = app.test_client()
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'ok'

    def test_chat_endpoint_unauthenticated(self, app):
        """Test chat endpoint without authentication"""
        client = app.test_client()
        response = client.post('/chat', json={'message': 'Hello'})
        assert response.status_code == 200  # Auth disabled for demo

    def test_mcp_headers(self):
        """Test MCP-specific headers are present"""
        response = self.client.get('/health')
        assert response.headers.get('X-MCP-Version') == '1.0'
        assert response.headers.get('X-MCP-Transport') == 'http'
        assert response.headers.get('Cache-Control') == 'no-cache'