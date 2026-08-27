"""Session-scoped command planning, approval and bounded execution."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from models.event_bus import EventBus
from term_mcp_deepseek.audit import AuditLog
from term_mcp_deepseek.domain import (
    ExecutionPlan,
    ExecutionReceipt,
    PlanStatus,
    utc_now,
)
from term_mcp_deepseek.policy import CommandPolicy


class ExecutionError(RuntimeError):
    pass


@dataclass
class SessionState:
    id: str
    plans: dict[str, ExecutionPlan] = field(default_factory=dict)
    receipts: dict[str, ExecutionReceipt] = field(default_factory=dict)
    active_process: subprocess.Popen | None = None
    active_plan_id: str | None = None
    paused: bool = False
    cancel_requested: bool = False
    last_activity: float = field(default_factory=time.time)
    lock: threading.RLock = field(default_factory=threading.RLock)


class SessionRegistry:
    def __init__(
        self,
        max_sessions: int = 10,
        timeout_seconds: int = 3600,
        on_close=None,
    ) -> None:
        self.max_sessions = max_sessions
        self.timeout_seconds = timeout_seconds
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()
        self.on_close = on_close

    def create(self) -> SessionState:
        with self._lock:
            self._cleanup_locked()
            if len(self._sessions) >= self.max_sessions:
                raise ExecutionError("maximum concurrent sessions reached")
            session = SessionState(id=str(uuid4()))
            self._sessions[session.id] = session
            return session

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            self._cleanup_locked()
            session = self._sessions.get(session_id)
            if session is None:
                raise ExecutionError("unknown or expired session")
            session.last_activity = time.time()
            return session

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session and session.active_process:
            _terminate_process(session.active_process)
        if session and self.on_close:
            self.on_close(session_id)

    def cleanup(self) -> None:
        with self._lock:
            self._cleanup_locked()

    def close_all(self) -> None:
        with self._lock:
            session_ids = list(self._sessions)
        for session_id in session_ids:
            self.close(session_id)

    def _cleanup_locked(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.last_activity > self.timeout_seconds
        ]
        for session_id in expired:
            session = self._sessions.pop(session_id)
            if session.active_process:
                _terminate_process(session.active_process)
            if self.on_close:
                self.on_close(session_id)


class ExecutionService:
    def __init__(
        self,
        policy: CommandPolicy,
        event_bus: EventBus,
        audit_log: AuditLog,
        max_sessions: int = 10,
        session_timeout: int = 3600,
        command_timeout: float = 20.0,
        max_output_bytes: int = 1_048_576,
    ) -> None:
        self.policy = policy
        self.event_bus = event_bus
        self.audit_log = audit_log
        self.command_timeout = command_timeout
        self.max_output_bytes = max_output_bytes
        self.sessions = SessionRegistry(max_sessions, session_timeout, event_bus.close)

    def create_session(self) -> dict[str, str]:
        session = self.sessions.create()
        return {"session_id": session.id}

    def close_session(self, session_id: str) -> None:
        self.sessions.close(session_id)
        self.event_bus.close(session_id)

    def plan(
        self,
        session_id: str,
        command: str,
        cwd: str | None = None,
    ) -> ExecutionPlan:
        session = self.sessions.get(session_id)
        selected_cwd = self.policy.resolve_cwd(cwd)
        decision = self.policy.analyze(command, selected_cwd)
        limits = {
            "timeout_seconds": self.command_timeout,
            "max_output_bytes": self.max_output_bytes,
            "max_processes_per_session": 1,
        }
        plan = ExecutionPlan(
            command=command,
            session_id=session_id,
            cwd=str(selected_cwd),
            mode=self.policy.mode,
            decision=decision,
            limits=limits,
            preview=_build_preview(decision, limits),
        )
        with session.lock:
            session.plans[plan.id] = plan
        self.event_bus.publish(session_id, {"type": "plan", "plan": plan.to_dict()})
        return plan

    def replan(self, session_id: str, plan_id: str) -> ExecutionPlan:
        previous = self._get_plan(session_id, plan_id)
        if previous.status in {PlanStatus.RUNNING, PlanStatus.PAUSED}:
            raise ExecutionError("running plans cannot be retried")
        return self.plan(session_id, previous.command, previous.cwd)

    def approve(self, session_id: str, plan_id: str) -> ExecutionPlan:
        plan = self._get_plan(session_id, plan_id)
        if plan.status is PlanStatus.BLOCKED:
            raise ExecutionError("blocked plans cannot be approved")
        if plan.status is not PlanStatus.PLANNED:
            raise ExecutionError(f"plan cannot be approved from {plan.status.value}")
        plan.status = PlanStatus.APPROVED
        plan.approved_at = utc_now()
        self.event_bus.publish(session_id, {"type": "approved", "plan": plan.to_dict()})
        return plan

    def execute(self, session_id: str, plan_id: str) -> ExecutionReceipt:
        session = self.sessions.get(session_id)
        plan = self._get_plan(session_id, plan_id)
        if plan.status is PlanStatus.BLOCKED:
            raise ExecutionError("blocked plans cannot be executed")
        if plan.decision.requires_approval and plan.status is not PlanStatus.APPROVED:
            raise ExecutionError("plan requires explicit approval")
        if plan.status not in {PlanStatus.PLANNED, PlanStatus.APPROVED}:
            raise ExecutionError(f"plan cannot execute from {plan.status.value}")

        with session.lock:
            if session.active_process is not None or session.active_plan_id is not None:
                raise ExecutionError("another command is already running in this session")
            session.cancel_requested = False
            session.active_plan_id = plan.id
            session.paused = False
            plan.status = PlanStatus.RUNNING
        started_at = utc_now()
        start = time.monotonic()
        self.event_bus.publish(
            session_id,
            {"type": "command_start", "plan": plan.to_dict()},
        )
        receipt = self._run_plan(session, plan, started_at, start)
        with session.lock:
            session.receipts[receipt.id] = receipt
        return receipt

    def pause(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        with session.lock:
            process = session.active_process
            plan = session.plans.get(session.active_plan_id or "")
            if process is None or plan is None or process.poll() is not None or session.paused:
                return False
            try:
                os.killpg(process.pid, signal.SIGSTOP)
            except ProcessLookupError:
                return False
            session.paused = True
            plan.status = PlanStatus.PAUSED
        self.event_bus.publish(session_id, {"type": "command_paused", "plan": plan.to_dict()})
        return True

    def resume(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        with session.lock:
            process = session.active_process
            plan = session.plans.get(session.active_plan_id or "")
            if process is None or plan is None or process.poll() is not None or not session.paused:
                return False
            try:
                os.killpg(process.pid, signal.SIGCONT)
            except ProcessLookupError:
                return False
            session.paused = False
            plan.status = PlanStatus.RUNNING
        self.event_bus.publish(session_id, {"type": "command_resumed", "plan": plan.to_dict()})
        return True

    def cancel(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        with session.lock:
            if session.active_process is None:
                return False
            session.cancel_requested = True
            _terminate_process(session.active_process)
            return True

    def latest_receipt(self, session_id: str) -> ExecutionReceipt | None:
        session = self.sessions.get(session_id)
        with session.lock:
            if not session.receipts:
                return None
            return next(reversed(session.receipts.values()))

    def _run_plan(
        self,
        session: SessionState,
        plan: ExecutionPlan,
        started_at: str,
        start: float,
    ) -> ExecutionReceipt:
        exit_code: int | None = None
        stdout = ""
        stderr = ""
        truncated = False
        approved = plan.approved_at is not None or not plan.decision.requires_approval
        final_status = PlanStatus.FAILED
        safe_environment = _safe_environment(Path(plan.cwd))

        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(
                    plan.decision.argv,
                    cwd=plan.cwd,
                    env=safe_environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True,
                )
                with session.lock:
                    session.active_process = process
                try:
                    exit_code = process.wait(timeout=self.command_timeout)
                    if session.cancel_requested:
                        final_status = PlanStatus.CANCELLED
                    else:
                        final_status = PlanStatus.SUCCEEDED if exit_code == 0 else PlanStatus.FAILED
                except subprocess.TimeoutExpired:
                    _terminate_process(process)
                    exit_code = process.wait()
                    final_status = PlanStatus.TIMED_OUT
                stdout, stdout_truncated = _read_limited(stdout_file, self.max_output_bytes)
                stderr, stderr_truncated = _read_limited(stderr_file, self.max_output_bytes)
                truncated = stdout_truncated or stderr_truncated
            except OSError as error:
                stderr = str(error)
                final_status = PlanStatus.FAILED
            finally:
                with session.lock:
                    session.active_process = None
                    session.active_plan_id = None
                    session.paused = False

        plan.status = final_status
        finished_at = utc_now()
        receipt = ExecutionReceipt(
            plan_id=plan.id,
            session_id=plan.session_id,
            command=plan.command,
            command_sha256=hashlib.sha256(plan.command.encode("utf-8")).hexdigest(),
            cwd=plan.cwd,
            mode=plan.mode,
            risk=plan.decision.risk,
            approved=approved,
            policy=plan.decision.to_dict(),
            status=final_status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round((time.monotonic() - start) * 1000),
            exit_code=exit_code,
            signal=-exit_code if exit_code is not None and exit_code < 0 else None,
            stdout=stdout,
            stderr=stderr,
            output_truncated=truncated,
        )
        receipt = self.audit_log.finalize(receipt)
        event_type = "command_complete" if final_status is PlanStatus.SUCCEEDED else "command_error"
        self.event_bus.publish(
            plan.session_id,
            {"type": event_type, "receipt": receipt.to_dict()},
        )
        return receipt

    def _get_plan(self, session_id: str, plan_id: str) -> ExecutionPlan:
        session = self.sessions.get(session_id)
        with session.lock:
            plan = session.plans.get(plan_id)
            if plan is None or plan.session_id != session_id:
                raise ExecutionError("plan does not belong to this session")
            return plan


def _safe_environment(workspace: Path) -> dict[str, str]:
    allowed = {"LANG", "LC_ALL", "TERM", "TMPDIR"}
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    path_entries = [
        str(workspace / ".venv" / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    for entry in os.environ.get("PATH", "").split(":"):
        if not entry:
            continue
        path = Path(entry)
        if not path.is_absolute():
            continue
        resolved = path.resolve()
        if resolved.is_relative_to(workspace):
            continue
        value = str(resolved)
        if value not in path_entries:
            path_entries.append(value)
    environment["PATH"] = ":".join(path_entries)
    environment["HOME"] = str(workspace)
    environment["PWD"] = str(workspace)
    environment["TERM_MCP_SANDBOX"] = "1"
    return environment


def _build_preview(decision, limits: dict[str, int | float]) -> dict[str, object]:
    argv = list(decision.argv)
    executable = Path(argv[0]).name if argv else "unknown"
    write_commands = {"cp", "mkdir", "mv", "rm", "touch"}
    files = []
    if executable in write_commands:
        files = [token for token in argv[1:] if not token.startswith("-")]
    network_commands = {("cargo", operation) for operation in {"add", "fetch", "install", "update"}}
    network_commands |= {("go", operation) for operation in {"get", "install"}}
    network_commands |= {
        (manager, operation)
        for manager in {"npm", "pnpm", "yarn"}
        for operation in {"add", "install", "update"}
    }
    network_commands |= {("uv", operation) for operation in {"add", "pip", "sync"}}
    operation = (executable, Path(argv[1]).name if len(argv) > 1 else "")
    return {
        "executable": executable,
        "files_potentially_touched": files or (["repository state"] if executable == "git" else []),
        "network_requested": operation in network_commands,
        "executes_project_code": any(
            "project-defined code" in reason for reason in decision.reasons
        ),
        "max_duration_seconds": limits["timeout_seconds"],
        "max_output_bytes": limits["max_output_bytes"],
        "risk": decision.risk.value,
    }


def _read_limited(handle, limit: int) -> tuple[str, bool]:
    handle.flush()
    size = handle.seek(0, os.SEEK_END)
    handle.seek(0)
    data = handle.read(limit + 1)
    truncated = size > limit
    if truncated:
        data = data[:limit]
    return data.decode("utf-8", "replace"), truncated


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGCONT)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=1)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


__all__ = [
    "ExecutionError",
    "ExecutionService",
    "SessionRegistry",
    "SessionState",
]
