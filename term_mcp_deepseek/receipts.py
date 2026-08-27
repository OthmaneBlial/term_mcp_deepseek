"""Schema validation, signature verification, and safe receipt summaries."""

from __future__ import annotations

import hashlib
import hmac
import json
from copy import deepcopy
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def receipt_schema() -> dict[str, Any]:
    resource = files("term_mcp_deepseek.schemas").joinpath("receipt.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


RECEIPT_VALIDATOR = Draft202012Validator(receipt_schema(), format_checker=FormatChecker())


def validate_receipt(payload: Any) -> list[str]:
    return [error.message for error in sorted(RECEIPT_VALIDATOR.iter_errors(payload), key=str)]


def verify_receipt_signature(payload: Any, signing_key: str) -> bool:
    if not isinstance(payload, dict) or not signing_key:
        return False
    signature = payload.get("signature")
    if not isinstance(signature, str):
        return False
    expected = sign_receipt_payload(payload, signing_key)
    return hmac.compare_digest(expected, signature)


def sign_receipt_payload(payload: dict[str, Any], signing_key: str) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def receipt_report(payload: Any, signing_key: str) -> dict[str, Any]:
    errors = validate_receipt(payload)
    return {
        "schema_valid": not errors,
        "signature_valid": not errors and verify_receipt_signature(payload, signing_key),
        "errors": errors,
    }


def redact_receipt_for_sharing(payload: Any, signing_key: str) -> dict[str, Any]:
    report = receipt_report(payload, signing_key)
    if not report["schema_valid"] or not report["signature_valid"]:
        raise ValueError("only a valid signed receipt can be redacted for sharing")
    redacted = deepcopy(payload)
    redacted["sharing_redacted"] = True
    redacted["command"] = "[REDACTED FOR SHARING]"
    redacted["cwd"] = "[REDACTED FOR SHARING]"
    redacted["stdout"] = "[REDACTED FOR SHARING]"
    redacted["stderr"] = "[REDACTED FOR SHARING]"
    redacted["policy"]["argv"] = []
    redacted["signature"] = sign_receipt_payload(redacted, signing_key)
    return redacted


def receipt_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "id",
            "status",
            "command",
            "cwd",
            "risk",
            "approved",
            "started_at",
            "finished_at",
            "duration_ms",
            "exit_code",
            "signal",
            "output_truncated",
        )
    }


__all__ = [
    "receipt_report",
    "receipt_schema",
    "receipt_summary",
    "redact_receipt_for_sharing",
    "sign_receipt_payload",
    "validate_receipt",
    "verify_receipt_signature",
]
