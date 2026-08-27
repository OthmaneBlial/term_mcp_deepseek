"""Versioned domain objects for safe terminal execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ApprovalMode(str, Enum):
    INSPECT = "inspect"
    CONFIRM = "confirm"
    TRUSTED = "trusted"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class PlanStatus(str, Enum):
    PLANNED = "planned"
    BLOCKED = "blocked"
    APPROVED = "approved"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class PolicyDecision:
    allowed: bool
    risk: RiskLevel
    requires_approval: bool
    reasons: list[str]
    argv: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["risk"] = self.risk.value
        return result


@dataclass
class ExecutionPlan:
    command: str
    session_id: str
    cwd: str
    mode: ApprovalMode
    decision: PolicyDecision
    limits: dict[str, int | float]
    preview: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0"
    status: PlanStatus = PlanStatus.PLANNED
    created_at: str = field(default_factory=utc_now)
    approved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.decision.allowed:
            self.status = PlanStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "session_id": self.session_id,
            "command": self.command,
            "cwd": self.cwd,
            "mode": self.mode.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "policy": self.decision.to_dict(),
            "limits": self.limits,
            "preview": self.preview,
        }


@dataclass
class ExecutionReceipt:
    plan_id: str
    session_id: str
    command: str
    command_sha256: str
    cwd: str
    mode: ApprovalMode
    risk: RiskLevel
    approved: bool
    policy: dict[str, Any]
    status: PlanStatus
    started_at: str
    finished_at: str
    duration_ms: int
    exit_code: int | None
    signal: int | None
    stdout: str
    stderr: str
    output_truncated: bool
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0"
    signature: str = ""

    def to_dict(self, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "id": self.id,
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "command": self.command,
            "command_sha256": self.command_sha256,
            "cwd": self.cwd,
            "mode": self.mode.value,
            "risk": self.risk.value,
            "approved": self.approved,
            "policy": self.policy,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "signal": self.signal,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output_truncated": self.output_truncated,
        }
        if include_signature:
            result["signature"] = self.signature
        return result


__all__ = [
    "ApprovalMode",
    "ExecutionPlan",
    "ExecutionReceipt",
    "PlanStatus",
    "PolicyDecision",
    "RiskLevel",
    "utc_now",
]
