def rpc(client, auth_headers, method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "method": method, "id": request_id}
    if params is not None:
        payload["params"] = params
    return client.post("/mcp", json=payload, headers=auth_headers)


def create_session(client, auth_headers):
    response = client.post("/sessions", headers=auth_headers)
    assert response.status_code == 201
    return response.get_json()["session_id"]


def test_sensitive_routes_fail_closed(client):
    assert client.post("/sessions").status_code == 401
    assert (
        client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        ).status_code
        == 401
    )
    assert client.post("/chat", json={"message": "hello"}).status_code == 401
    assert client.get("/stream?session_id=unknown").status_code == 401


def test_mcp_initialize_and_list_tools(client, auth_headers):
    initialized = rpc(
        client,
        auth_headers,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "tests", "version": "1"},
        },
    )
    listed = rpc(client, auth_headers, "tools/list", request_id=2)

    assert initialized.status_code == 200
    assert initialized.get_json()["result"]["serverInfo"]["version"] == "0.9.0"
    assert {tool["name"] for tool in listed.get_json()["result"]["tools"]} == {
        "terminal_plan",
        "terminal_approve",
        "terminal_execute",
        "terminal_cancel",
        "terminal_receipt",
    }


def test_safe_plan_executes_and_returns_signed_receipt(client, auth_headers):
    session_id = create_session(client, auth_headers)
    planned = rpc(
        client,
        auth_headers,
        "tools/call",
        {
            "name": "terminal_plan",
            "arguments": {"session_id": session_id, "command": "pwd"},
        },
    ).get_json()["result"]["structuredContent"]
    executed = rpc(
        client,
        auth_headers,
        "tools/call",
        {
            "name": "terminal_execute",
            "arguments": {"session_id": session_id, "plan_id": planned["id"]},
        },
    )
    receipt = executed.get_json()["result"]["structuredContent"]

    assert planned["status"] == "planned"
    assert planned["policy"]["requires_approval"] is False
    assert planned["mode"] == "inspect"
    assert planned["limits"]["max_processes_per_session"] == 1
    assert executed.status_code == 200
    assert receipt["status"] == "succeeded"
    assert receipt["stdout"].strip()
    assert receipt["policy"]["reasons"]
    assert receipt["signal"] is None
    assert len(receipt["signature"]) == 64


def test_blocked_plan_never_executes(client, auth_headers):
    session_id = create_session(client, auth_headers)
    planned = rpc(
        client,
        auth_headers,
        "tools/call",
        {
            "name": "terminal_plan",
            "arguments": {
                "session_id": session_id,
                "command": "cat /etc/passwd",
            },
        },
    ).get_json()["result"]["structuredContent"]
    executed = rpc(
        client,
        auth_headers,
        "tools/call",
        {
            "name": "terminal_execute",
            "arguments": {"session_id": session_id, "plan_id": planned["id"]},
        },
    )

    assert planned["status"] == "blocked"
    assert "escapes the workspace" in planned["policy"]["reasons"][0]
    assert executed.status_code == 400
    assert executed.get_json()["error"]["code"] == -32010


def test_mcp_returns_protocol_error(client, auth_headers):
    response = rpc(client, auth_headers, "unknown/method", request_id="request-1")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32601
    assert response.get_json()["id"] == "request-1"


def test_mcp_rejects_invalid_json(client, auth_headers):
    response = client.post(
        "/mcp",
        data="{",
        content_type="application/json",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32700


def test_mcp_notification_has_no_body(client, auth_headers):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "ping"},
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert response.data == b""


def test_empty_chat_is_rejected_before_model_call(client, auth_headers):
    response = client.post("/chat", json={}, headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_request"


def test_origin_allowlist_is_enforced(client, auth_headers):
    denied = client.post(
        "/sessions",
        headers={**auth_headers, "Origin": "https://evil.example"},
    )
    allowed = client.post(
        "/sessions",
        headers={**auth_headers, "Origin": "http://localhost:8000"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 201
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:8000"
