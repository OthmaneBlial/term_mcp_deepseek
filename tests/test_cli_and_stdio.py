import io
import json

from term_mcp_deepseek import cli
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


def test_version_command(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.9.0"


def test_token_command_generates_strong_secret(capsys):
    assert main(["token"]) == 0
    assert len(capsys.readouterr().out.strip()) >= 32


def test_serve_generates_missing_token_once(monkeypatch, tmp_path, capsys):
    captured = {}

    class FakeApp:
        def run(self, **kwargs):
            captured["run"] = kwargs

    def fake_create_app(settings):
        captured["settings"] = settings
        return FakeApp()

    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(cli.secrets, "token_urlsafe", lambda _size: "g" * 43)
    monkeypatch.setattr("term_mcp_deepseek.app.create_app", fake_create_app)

    assert main(["serve"]) == 0
    assert captured["settings"].auth_token == "g" * 43
    assert captured["run"]["host"] == "127.0.0.1"
    assert ("g" * 43) in capsys.readouterr().err


def test_serve_rejects_explicit_weak_token(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUTH_TOKEN", "weak")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    assert main(["serve"]) == 2
    assert "AUTH_TOKEN must contain at least 32 characters" in capsys.readouterr().err


def test_stdio_dispatches_and_keeps_stdout_json_only(tmp_path):
    reader = io.StringIO('{"jsonrpc":"2.0","method":"tools/list","id":1}\nnot-json\n')
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
    assert responses[0]["result"]["tools"]
    assert responses[1]["error"]["code"] == -32700
