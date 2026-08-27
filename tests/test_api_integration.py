MODERN_VERSION = "2026-07-28"
MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
    "io.modelcontextprotocol/clientInfo": {"name": "pytest", "version": "1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def rpc(client, auth_headers, method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "method": method, "id": request_id}
    selected_params = dict(params or {})
    selected_params["_meta"] = MODERN_META
    payload["params"] = selected_params
    headers = {
        **auth_headers,
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MODERN_VERSION,
        "Mcp-Method": method,
    }
    name_key = {"tools/call": "name", "resources/read": "uri", "prompts/get": "name"}.get(method)
    if name_key:
        headers["Mcp-Name"] = selected_params[name_key]
    return client.post("/mcp", json=payload, headers=headers)


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


def test_mcp_discover_and_list_tools(client, auth_headers):
    discovered = rpc(client, auth_headers, "server/discover")
    listed = rpc(client, auth_headers, "tools/list", request_id=2)

    assert discovered.status_code == 200
    assert discovered.get_json()["result"]["supportedVersions"] == [
        "2026-07-28",
        "2025-11-25",
    ]
    assert (
        discovered.get_json()["result"]["_meta"]["io.modelcontextprotocol/serverInfo"]["version"]
        == "0.9.0"
    )
    assert listed.get_json()["result"]["resultType"] == "complete"
    assert {tool["name"] for tool in listed.get_json()["result"]["tools"]} == {
        "terminal_plan",
        "terminal_approve",
        "terminal_execute",
        "terminal_retry",
        "terminal_pause",
        "terminal_resume",
        "terminal_cancel",
        "terminal_receipt",
    }


def test_legacy_initialize_session_lifecycle(client, auth_headers):
    accept = "application/json, text/event-stream"
    initialized = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "legacy-tests", "version": "1"},
            },
        },
        headers={**auth_headers, "Accept": accept},
    )
    session_id = initialized.headers["Mcp-Session-Id"]
    legacy_headers = {
        **auth_headers,
        "Accept": accept,
        "MCP-Protocol-Version": "2025-11-25",
        "Mcp-Session-Id": session_id,
    }
    ready = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=legacy_headers,
    )
    listed = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers=legacy_headers,
    )
    terminated = client.delete(
        "/mcp",
        headers={**auth_headers, "Mcp-Session-Id": session_id},
    )

    assert initialized.status_code == 200
    assert initialized.get_json()["result"]["protocolVersion"] == "2025-11-25"
    assert ready.status_code == 202
    assert listed.status_code == 200
    assert listed.get_json()["result"]["tools"]
    assert terminated.status_code == 200


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

    validated = client.post(
        "/receipts/validate",
        json={"receipt": receipt},
        headers=auth_headers,
    )
    assert validated.status_code == 200
    assert validated.get_json() == {
        "errors": [],
        "schema_valid": True,
        "signature_valid": True,
    }

    shared_response = client.post(
        "/receipts/redact",
        json={"receipt": receipt},
        headers=auth_headers,
    )
    shared = shared_response.get_json()["receipt"]
    assert shared_response.status_code == 200
    assert shared["sharing_redacted"] is True
    assert shared["stdout"] == "[REDACTED FOR SHARING]"
    assert shared["cwd"] == "[REDACTED FOR SHARING]"
    assert (
        client.post(
            "/receipts/validate",
            json={"receipt": shared},
            headers=auth_headers,
        ).get_json()["signature_valid"]
        is True
    )


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
    assert executed.status_code == 200
    assert executed.get_json()["result"]["isError"] is True
    assert executed.get_json()["result"]["structuredContent"]["code"] == "tool_execution_error"


def test_mcp_returns_protocol_error(client, auth_headers):
    response = rpc(client, auth_headers, "unknown/method", request_id="request-1")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == -32601
    assert response.get_json()["id"] == "request-1"


def test_modern_transport_rejects_unsupported_version(client, auth_headers):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "server/discover",
        "params": {
            "_meta": {
                **MODERN_META,
                "io.modelcontextprotocol/protocolVersion": "1900-01-01",
            }
        },
    }
    response = client.post(
        "/mcp",
        json=payload,
        headers={
            **auth_headers,
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "1900-01-01",
            "Mcp-Method": "server/discover",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32022
    assert response.get_json()["error"]["data"]["supported"][0] == MODERN_VERSION


def test_modern_transport_rejects_header_mismatch_and_missing_accept(client, auth_headers):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "terminal_plan",
            "arguments": {"command": "pwd"},
            "_meta": MODERN_META,
        },
    }
    common = {
        **auth_headers,
        "MCP-Protocol-Version": MODERN_VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "wrong-name",
    }
    mismatch = client.post(
        "/mcp",
        json=payload,
        headers={**common, "Accept": "application/json, text/event-stream"},
    )
    unacceptable = client.post("/mcp", json=payload, headers=common)

    assert mismatch.status_code == 400
    assert mismatch.get_json()["error"]["code"] == -32020
    assert unacceptable.status_code == 406
    assert unacceptable.get_json()["error"]["code"] == -32020


def test_legacy_request_requires_a_live_transport_session(client, auth_headers):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={
            **auth_headers,
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-11-25",
            "Mcp-Session-Id": "not-a-session",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == -32600


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
    response = rpc(client, auth_headers, "ping", request_id=None)

    assert response.status_code == 200
    assert response.get_json()["id"] is None


def test_mcp_notification_without_id_is_accepted(client, auth_headers):
    payload = {
        "jsonrpc": "2.0",
        "method": "ping",
        "params": {"_meta": MODERN_META},
    }
    response = client.post(
        "/mcp",
        json=payload,
        headers={
            **auth_headers,
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": MODERN_VERSION,
            "Mcp-Method": "ping",
        },
    )

    assert response.status_code == 202
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
