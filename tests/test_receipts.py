import json

from term_mcp_deepseek.cli import main
from term_mcp_deepseek.domain import ApprovalMode
from term_mcp_deepseek.receipts import (
    receipt_report,
    receipt_summary,
    redact_receipt_for_sharing,
)
from tests.test_execution import TOKEN, make_service


def create_receipt(tmp_path):
    service, _audit, _path = make_service(tmp_path, mode=ApprovalMode.INSPECT)
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "pwd")
    return service.execute(session_id, plan.id).to_dict()


def test_receipt_schema_signature_and_tamper_detection(tmp_path):
    receipt = create_receipt(tmp_path)

    assert receipt_report(receipt, TOKEN) == {
        "schema_valid": True,
        "signature_valid": True,
        "errors": [],
    }
    receipt["stdout"] = "tampered"
    assert receipt_report(receipt, TOKEN)["signature_valid"] is False
    receipt["status"] = "invented"
    assert receipt_report(receipt, TOKEN)["schema_valid"] is False


def test_cli_validates_and_summarizes_exported_receipt(tmp_path, monkeypatch, capsys):
    receipt = create_receipt(tmp_path)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setenv("AUTH_TOKEN", TOKEN)

    assert main(["receipt", "validate", str(path)]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["signature_valid"] is True

    assert main(["receipt", "show", str(path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary == receipt_summary(receipt)
    assert "stdout" not in summary


def test_cli_demo_requires_no_model_key(monkeypatch, capsys):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    assert main(["demo", "--json"]) == 0
    scenarios = json.loads(capsys.readouterr().out)["scenarios"]
    assert {scenario["command"] for scenario in scenarios} >= {"pwd", "sleep 15"}


def test_shareable_receipt_removes_private_content_and_remains_valid(tmp_path):
    receipt = create_receipt(tmp_path)

    shared = redact_receipt_for_sharing(receipt, TOKEN)

    assert shared["sharing_redacted"] is True
    assert shared["command"] == "[REDACTED FOR SHARING]"
    assert shared["cwd"] == "[REDACTED FOR SHARING]"
    assert shared["stdout"] == "[REDACTED FOR SHARING]"
    assert shared["stderr"] == "[REDACTED FOR SHARING]"
    assert shared["policy"]["argv"] == []
    assert shared["signature"] != receipt["signature"]
    assert receipt_report(shared, TOKEN)["signature_valid"] is True


def test_invalid_receipt_cannot_be_redacted_for_sharing(tmp_path):
    receipt = create_receipt(tmp_path)
    receipt["stdout"] = "tampered"

    try:
        redact_receipt_for_sharing(receipt, TOKEN)
    except ValueError as error:
        assert "valid signed receipt" in str(error)
    else:
        raise AssertionError("tampered receipt was accepted")
