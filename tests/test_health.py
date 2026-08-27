def test_health_reports_version(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["version"] == "0.9.0"
    assert response.headers["X-MCP-Version"] == "2026-07-28"


def test_root_serves_chat(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Term MCP DeepSeek" in response.data


def test_info_uses_package_version(client, auth_headers):
    response = client.get("/mcp/info", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["version"] == "0.9.0"
