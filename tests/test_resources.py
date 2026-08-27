import pytest

from models.event_bus import EventBus
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.server import MCPServer
from tools.json_rpc import JSONRPCError

TOKEN = "resource-test-token-that-is-longer-than-thirty-two"


def make_server(tmp_path):
    return MCPServer(
        Settings(
            workspace_root=str(tmp_path),
            auth_token=TOKEN,
        ),
        EventBus(),
    )


def test_roots_expose_only_configured_workspace(tmp_path):
    server = make_server(tmp_path)

    roots = server.list_roots()["roots"]

    assert roots == [{"uri": "workspace:///", "name": tmp_path.name}]
    assert "file:///" not in str(roots)


def test_resource_traversal_and_symlink_are_blocked(tmp_path):
    server = make_server(tmp_path)
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("outside")
    (tmp_path / "link").symlink_to(outside)

    with pytest.raises(JSONRPCError, match="outside"):
        server.read_resource("workspace:///../outside-secret.txt")
    with pytest.raises(JSONRPCError, match="symlink"):
        server.read_resource("workspace:///link")


def test_resource_content_is_redacted(tmp_path):
    server = make_server(tmp_path)
    (tmp_path / "settings.txt").write_text(f"AUTH_TOKEN={TOKEN}\napi_key=private-value\n")

    content = server.read_resource("workspace:///settings.txt")["contents"][0]["text"]

    assert TOKEN not in content
    assert "private-value" not in content
    assert content.count("[REDACTED]") == 2
