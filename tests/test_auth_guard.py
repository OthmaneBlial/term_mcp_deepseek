from server_new import create_app
from tools.auth import JWTAuth

def test_chat_requires_auth(monkeypatch):
    app = create_app()
    client = app.test_client()

    r = client.post("/chat", json={})
    assert r.status_code == 401

    # mint token
    from tools import auth as auth_module
    token = auth_module.auth.create("tester")

    r2 = client.post("/chat", headers={"Authorization": f"Bearer {token}"}, json={})
    assert r2.status_code in (200, 400)  # depends on your handler validation