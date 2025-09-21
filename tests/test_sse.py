import pytest
from server import app

def test_stream_hello():
    app.config['TESTING'] = True
    client = app.test_client()
    # bypass auth by setting optional=True or inject a valid token
    rv = client.get("/stream?session_id=t1", headers={"Authorization":"Bearer testtoken"}, buffered=True)
    assert rv.status_code == 200
    body = b"".join(rv.response)[:200].decode("utf-8", "ignore")
    assert "event: hello" in body