import pytest

from models.event_bus import EventBus
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.server import MCPServer
from tools.json_rpc import JSONRPCError

TOKEN = "server-test-token-that-is-longer-than-thirty-two"


def make_server(tmp_path):
    return MCPServer(
        Settings(workspace_root=str(tmp_path), auth_token=TOKEN),
        EventBus(),
    )


def test_model_cmd_marker_is_inert_text(tmp_path, monkeypatch):
    server = make_server(tmp_path)
    monkeypatch.setattr(
        server.deepseek,
        "chat",
        lambda _messages: "CMD: touch model-created.txt",
    )

    response = server.handle_chat({"message": "create a file"})

    assert response["message"] == "CMD: touch model-created.txt"
    assert len(response["session_id"]) == 36
    assert not (tmp_path / "model-created.txt").exists()


def test_chat_histories_are_session_isolated(tmp_path, monkeypatch):
    server = make_server(tmp_path)
    monkeypatch.setattr(
        server.deepseek,
        "chat",
        lambda messages: f"reply:{messages[-1]['content']}",
    )

    first = server.handle_chat({"message": "first-private-message"})
    second = server.handle_chat({"message": "second-private-message"})

    first_history = server._conversations[first["session_id"]]
    second_history = server._conversations[second["session_id"]]
    assert all("second-private-message" not in item["content"] for item in first_history)
    assert all("first-private-message" not in item["content"] for item in second_history)


def test_legacy_direct_execution_tools_are_removed(tmp_path):
    server = make_server(tmp_path)

    with pytest.raises(JSONRPCError, match="plan/approve/execute"):
        server.call_tool(
            "write_to_terminal",
            {"command": "pwd"},
        )


def test_prompt_never_requests_implicit_execution(tmp_path):
    server = make_server(tmp_path)

    prompt = server.get_prompt(
        "safe_terminal_task",
        {"task": "inspect the repository"},
    )

    text = prompt["messages"][0]["content"]["text"]
    assert "without executing" in text
    assert "configured workspace" in text


def test_unknown_prompt_is_structured_error(tmp_path):
    server = make_server(tmp_path)

    with pytest.raises(JSONRPCError) as raised:
        server.get_prompt("unknown")

    assert raised.value.code == -32602


def test_tool_arguments_follow_declared_schema(tmp_path):
    server = make_server(tmp_path)

    unexpected = server.call_tool(
        "terminal_plan",
        {"session_id": "session-1234", "command": "pwd", "surprise": True},
    )
    wrong_type = server.call_tool(
        "terminal_plan",
        {"session_id": "session-1234", "command": 123},
    )

    assert unexpected["isError"] is True
    assert "unexpected tool arguments" in unexpected["structuredContent"]["message"]
    assert wrong_type["isError"] is True
