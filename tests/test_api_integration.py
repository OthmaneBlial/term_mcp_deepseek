def test_mcp_lists_tools(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == 1
    assert {tool["name"] for tool in body["result"]["tools"]} == {
        "write_to_terminal",
        "read_terminal_output",
        "send_control_character",
    }


def test_mcp_returns_protocol_error(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "unknown/method", "id": "request-1"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32601
    assert response.get_json()["id"] == "request-1"


def test_mcp_rejects_invalid_json(client):
    response = client.post("/mcp", data="{", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32700


def test_mcp_notification_has_no_body(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list"},
    )

    assert response.status_code == 204
    assert response.data == b""


def test_empty_chat_is_safe_without_model_key(client):
    response = client.post("/chat", json={})

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "(No message provided)",
        "session_id": "default",
    }
