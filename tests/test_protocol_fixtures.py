import base64
import json
from pathlib import Path

from mcp import types

FIXTURES = Path(__file__).parent / "fixtures" / "protocol"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def modern_headers(auth_headers, payload):
    params = payload["params"]
    headers = {
        **auth_headers,
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": params["_meta"]["io.modelcontextprotocol/protocolVersion"],
        "Mcp-Method": payload["method"],
    }
    if payload["method"] == "tools/call":
        headers["Mcp-Name"] = params["name"]
    return headers


def test_modern_discover_fixture_matches_official_schema(client, auth_headers):
    payload = load_fixture("modern_discover.json")
    response = client.post("/mcp", json=payload, headers=modern_headers(auth_headers, payload))
    envelope = types.JSONRPCResponse.model_validate(response.get_json())
    result = types.DiscoverResult.model_validate(envelope.result)

    assert response.status_code == 200
    assert result.supported_versions[0] == "2026-07-28"
    assert result.result_type == "complete"


def test_modern_call_fixture_matches_official_schema(client, auth_headers):
    payload = load_fixture("modern_plan.json")
    response = client.post("/mcp", json=payload, headers=modern_headers(auth_headers, payload))
    envelope = types.JSONRPCResponse.model_validate(response.get_json())
    result = types.CallToolResult.model_validate(envelope.result)

    assert response.status_code == 200
    assert result.is_error is False
    assert result.structured_content["status"] == "planned"


def test_legacy_initialize_fixture_matches_official_schema(client, auth_headers):
    payload = load_fixture("legacy_initialize.json")
    response = client.post(
        "/mcp",
        json=payload,
        headers={**auth_headers, "Accept": "application/json, text/event-stream"},
    )
    envelope = types.JSONRPCResponse.model_validate(response.get_json())
    result = types.InitializeResult.model_validate(envelope.result)

    assert response.status_code == 200
    assert result.protocol_version == "2025-11-25"
    assert response.headers["Mcp-Session-Id"]


def test_base64_encoded_mcp_name_is_validated_after_decoding(client, auth_headers, tmp_path):
    filename = "résumé.txt"
    (tmp_path / filename).write_text("safe", encoding="utf-8")
    payload = load_fixture("modern_plan.json")
    payload["method"] = "resources/read"
    payload["params"] = {
        "uri": f"workspace:///{filename}",
        "_meta": payload["params"]["_meta"],
    }
    encoded = base64.b64encode(payload["params"]["uri"].encode()).decode()
    headers = modern_headers(auth_headers, payload)
    headers["Mcp-Name"] = f"=?base64?{encoded}?="

    response = client.post("/mcp", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.get_json()["result"]["contents"][0]["text"] == "safe"
