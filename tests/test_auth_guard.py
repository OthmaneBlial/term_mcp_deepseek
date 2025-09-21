import pytest

def test_chat_no_auth_required(app):
    """Chat endpoint currently doesn't require auth for demo purposes"""
    client = app.test_client()

    r = client.post("/chat", json={})
    assert r.status_code == 200  # Auth disabled for demo