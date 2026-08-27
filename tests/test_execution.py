import json
import threading
import time

import pytest

from models.event_bus import EventBus
from term_mcp_deepseek.audit import AuditLog, SecretRedactor
from term_mcp_deepseek.domain import ApprovalMode, PlanStatus
from term_mcp_deepseek.execution import ExecutionError, ExecutionService
from term_mcp_deepseek.policy import CommandPolicy

TOKEN = "execution-test-token-that-is-longer-than-thirty-two"


def make_service(
    tmp_path,
    *,
    mode=ApprovalMode.CONFIRM,
    timeout=2,
    output_limit=1024,
):
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path, TOKEN, SecretRedactor([TOKEN]))
    service = ExecutionService(
        CommandPolicy(tmp_path, mode=mode),
        EventBus(),
        audit,
        command_timeout=timeout,
        max_output_bytes=output_limit,
    )
    return service, audit, audit_path


def test_confirm_mode_requires_approval_and_writes_receipt(tmp_path):
    service, audit, audit_path = make_service(tmp_path)
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "touch note.txt")

    with pytest.raises(ExecutionError, match="approval"):
        service.execute(session_id, plan.id)

    service.approve(session_id, plan.id)
    receipt = service.execute(session_id, plan.id)

    assert (tmp_path / "note.txt").exists()
    assert receipt.status is PlanStatus.SUCCEEDED
    assert receipt.approved is True
    assert receipt.policy["risk"] == "high"
    assert receipt.policy["reasons"] == ["command can modify workspace files"]
    assert audit.verify(receipt) is True
    logged = json.loads(audit_path.read_text().strip())
    assert logged["id"] == receipt.id
    assert len(logged["signature"]) == 64


def test_output_is_bounded_without_loading_unlimited_data(tmp_path):
    (tmp_path / "large.txt").write_text("x" * 4096)
    service, _audit, _path = make_service(
        tmp_path,
        mode=ApprovalMode.INSPECT,
        output_limit=128,
    )
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "cat large.txt")
    receipt = service.execute(session_id, plan.id)

    assert receipt.status is PlanStatus.SUCCEEDED
    assert receipt.output_truncated is True
    assert len(receipt.stdout.encode()) == 128


def test_timeout_has_unambiguous_terminal_state(tmp_path):
    service, _audit, _path = make_service(tmp_path, timeout=0.05)
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "sleep 1")
    service.approve(session_id, plan.id)

    receipt = service.execute(session_id, plan.id)

    assert receipt.status is PlanStatus.TIMED_OUT
    assert receipt.exit_code is not None
    assert receipt.signal is not None


def test_active_process_can_be_cancelled(tmp_path):
    service, _audit, _path = make_service(tmp_path, timeout=5)
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "sleep 3")
    service.approve(session_id, plan.id)
    result = {}

    thread = threading.Thread(
        target=lambda: result.setdefault(
            "receipt",
            service.execute(session_id, plan.id),
        )
    )
    thread.start()
    for _attempt in range(100):
        if service.sessions.get(session_id).active_process is not None:
            break
        time.sleep(0.01)

    assert service.cancel(session_id) is True
    thread.join(timeout=2)

    assert thread.is_alive() is False
    assert result["receipt"].status is PlanStatus.CANCELLED
    assert result["receipt"].signal is not None


def test_plan_cannot_cross_session_boundary(tmp_path):
    service, _audit, _path = make_service(tmp_path, mode=ApprovalMode.INSPECT)
    first = service.create_session()["session_id"]
    second = service.create_session()["session_id"]
    plan = service.plan(first, "pwd")

    with pytest.raises(ExecutionError, match="does not belong"):
        service.execute(second, plan.id)


def test_session_event_queues_are_isolated(tmp_path):
    service, _audit, _path = make_service(tmp_path, mode=ApprovalMode.INSPECT)
    first = service.create_session()["session_id"]
    second = service.create_session()["session_id"]

    first_subscriber, first_queue = service.event_bus.subscribe(first)
    second_subscriber, second_queue = service.event_bus.subscribe(second)
    first_plan = service.plan(first, "pwd")
    second_plan = service.plan(second, "ls")
    first_event = first_queue.get_nowait()
    second_event = second_queue.get_nowait()

    assert first_event["plan"]["id"] == first_plan.id
    assert second_event["plan"]["id"] == second_plan.id
    assert first_event["plan"]["session_id"] != second_event["plan"]["session_id"]
    service.event_bus.unsubscribe(first, first_subscriber)
    service.event_bus.unsubscribe(second, second_subscriber)
    assert service.event_bus.subscriber_count(first) == 0


def test_execution_can_pause_resume_cancel_and_replan(tmp_path):
    service, _audit, _path = make_service(tmp_path, mode=ApprovalMode.INSPECT, timeout=5)
    session_id = service.create_session()["session_id"]
    plan = service.plan(session_id, "sleep 3")
    assert plan.preview["max_duration_seconds"] == 5
    assert plan.preview["risk"] == "medium"
    service.approve(session_id, plan.id)
    result = {}

    thread = threading.Thread(
        target=lambda: result.setdefault("receipt", service.execute(session_id, plan.id))
    )
    thread.start()
    for _attempt in range(100):
        if service.sessions.get(session_id).active_process is not None:
            break
        time.sleep(0.01)

    assert service.pause(session_id) is True
    assert plan.status is PlanStatus.PAUSED
    assert service.resume(session_id) is True
    assert plan.status is PlanStatus.RUNNING
    assert service.cancel(session_id) is True
    thread.join(timeout=2)

    assert result["receipt"].status is PlanStatus.CANCELLED
    retry = service.replan(session_id, plan.id)
    assert retry.id != plan.id
    assert retry.command == plan.command


def test_redactor_removes_known_and_labeled_secrets():
    redactor = SecretRedactor([TOKEN])
    text = f"AUTH_TOKEN={TOKEN} api_key=super-secret"

    redacted = redactor.redact(text)

    assert TOKEN not in redacted
    assert "super-secret" not in redacted
    assert redacted.count("[REDACTED]") == 2
