"""Redacted, signed execution receipts."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
from pathlib import Path
from typing import Any

from term_mcp_deepseek.domain import ExecutionReceipt

SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret|token)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


class SecretRedactor:
    def __init__(self, known_secrets: list[str] | None = None) -> None:
        self.known_secrets = [secret for secret in (known_secrets or []) if secret]

    def redact(self, value: str) -> str:
        redacted = value
        for secret in self.known_secrets:
            redacted = redacted.replace(secret, "[REDACTED]")
        return SENSITIVE_ASSIGNMENT.sub(
            lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
            redacted,
        )


class AuditLog:
    def __init__(
        self,
        path: str | Path | None,
        signing_key: str,
        redactor: SecretRedactor,
    ) -> None:
        self.path = Path(path).resolve() if path else None
        self.signing_key = signing_key.encode("utf-8")
        self.redactor = redactor
        self._lock = threading.Lock()

    def finalize(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        receipt.command = self.redactor.redact(receipt.command)
        receipt.policy = _redact_value(receipt.policy, self.redactor)
        receipt.stdout = self.redactor.redact(receipt.stdout)
        receipt.stderr = self.redactor.redact(receipt.stderr)
        receipt.signature = self.sign(receipt.to_dict(include_signature=False))
        if self.path:
            self.append(receipt)
        return receipt

    def sign(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self.signing_key, canonical, hashlib.sha256).hexdigest()

    def verify(self, receipt: ExecutionReceipt) -> bool:
        expected = self.sign(receipt.to_dict(include_signature=False))
        return hmac.compare_digest(expected, receipt.signature)

    def append(self, receipt: ExecutionReceipt) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _redact_value(value: Any, redactor: SecretRedactor) -> Any:
    if isinstance(value, str):
        return redactor.redact(value)
    if isinstance(value, list):
        return [_redact_value(item, redactor) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item, redactor) for key, item in value.items()}
    return value


__all__ = ["AuditLog", "SecretRedactor"]
