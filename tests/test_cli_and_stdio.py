import io
import json

from term_mcp_deepseek import __version__, cli
from term_mcp_deepseek.cli import main
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.stdio import serve_streams


def test_doctor_json(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "AUTH_TOKEN",
        "doctor-token-that-is-longer-than-thirty-two-characters",
    )

    exit_code = main(["doctor", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["checks"]["deepseek_key"]["required"] is False
    assert report["checks"]["auth_token"]["ok"] is True
    assert report["checks"]["configuration"]["ok"] is True
    assert report["checks"]["stdio_transport"]["ok"] is True
    assert report["checks"]["workspace_read"]["ok"] is True


def test_version_command(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_token_command_generates_strong_secret(capsys):
    assert main(["token"]) == 0
    assert len(capsys.readouterr().out.strip()) >= 32


def test_serve_generates_missing_token_once(monkeypatch, tmp_path, capsys):
    captured = {}

    class FakeApp:
        def close_term_mcp(self):
            captured["closed"] = True

    def fake_create_app(settings):
        captured["settings"] = settings
        return FakeApp()

    def fake_serve(app, **kwargs):
        captured["serve"] = kwargs

    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(cli.secrets, "token_urlsafe", lambda _size: "g" * 43)
    monkeypatch.setattr("term_mcp_deepseek.app.create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_http", fake_serve)

    assert main(["serve"]) == 0
    assert captured["settings"].auth_token == "g" * 43
    assert captured["serve"]["host"] == "127.0.0.1"
    assert captured["serve"]["debug"] is False
    assert captured["closed"] is True
    assert ("g" * 43) in capsys.readouterr().err


def test_doctor_connectivity_is_optional_without_model_key(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTH_TOKEN", "d" * 40)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    assert main(["doctor", "--connectivity", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    connectivity = report["checks"]["deepseek_connectivity"]
    assert connectivity["ok"] is False
    assert connectivity["required"] is False


def test_serve_rejects_explicit_weak_token(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUTH_TOKEN", "weak")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    assert main(["serve"]) == 2
    assert "AUTH_TOKEN must contain at least 32 characters" in capsys.readouterr().err


def test_stdio_dispatches_and_keeps_stdout_json_only(tmp_path):
    request = {
        "jsonrpc": "2.0",
        "method": "server/discover",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientInfo": {"name": "tests", "version": "1"},
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
        "id": 1,
    }
    reader = io.StringIO(json.dumps(request) + "\nnot-json\n")
    writer = io.StringIO()
    errors = io.StringIO()

    exit_code = serve_streams(
        reader,
        writer,
        errors,
        Settings(workspace_root=str(tmp_path)),
    )
    responses = [json.loads(line) for line in writer.getvalue().splitlines()]

    assert exit_code == 0
    assert responses[0]["result"]["supportedVersions"]
    assert responses[0]["result"]["resultType"] == "complete"
    assert responses[1]["error"]["code"] == -32700
