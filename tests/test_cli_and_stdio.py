import io
import json

from term_mcp_deepseek.cli import main
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.stdio import serve_streams


def test_doctor_json(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    exit_code = main(["doctor", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["checks"]["deepseek_key"]["required"] is False


def test_version_command(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.9.0"


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
