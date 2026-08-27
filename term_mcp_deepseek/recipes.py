"""Strict, inspect-only community recipes executed through the normal engine."""

from __future__ import annotations

import json
import secrets
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from models.event_bus import EventBus
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.domain import RiskLevel
from term_mcp_deepseek.server import MCPServer


class RecipeError(ValueError):
    """A recipe is malformed, unsafe, or did not produce its declared outcome."""


def recipe_schema() -> dict[str, Any]:
    resource = files("term_mcp_deepseek.schemas").joinpath("recipe.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


RECIPE_VALIDATOR = Draft202012Validator(recipe_schema())


def load_recipe(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RecipeError(f"cannot read recipe {path}: {error}") from error
    if not isinstance(payload, dict):
        raise RecipeError("recipe root must be an object")
    return payload


def validate_recipe(payload: Any, workspace: Path) -> list[str]:
    errors = [error.message for error in sorted(RECIPE_VALIDATOR.iter_errors(payload), key=str)]
    if errors or not isinstance(payload, dict):
        return errors

    permissions = payload["permissions"]
    if permissions != {"mode": "inspect", "network": False, "writes": False}:
        errors.append("public recipes must be inspect-only, network-free, and read-only")
        return errors
    if payload["risk"] != "low":
        errors.append("public inspect recipes must declare low risk")
        return errors

    settings = replace(
        Settings.from_env(),
        workspace_root=str(workspace.resolve()),
        approval_mode="inspect",
        allow_network=False,
        auth_token="recipe-validation-token-that-is-longer-than-thirty-two",
        audit_log="",
    )
    server = MCPServer(settings, EventBus())
    try:
        for index, step in enumerate(payload["steps"], start=1):
            decision = server.policy.analyze(step["command"], step.get("cwd"))
            if not decision.allowed:
                errors.append(f"step {index} is blocked: {decision.reasons[0]}")
            elif decision.requires_approval:
                errors.append(f"step {index} unexpectedly requires approval")
            elif decision.risk is not RiskLevel.LOW:
                errors.append(f"step {index} is not low risk")
    finally:
        server.execution.sessions.close_all()
    return errors


def validate_recipe_file(path: Path, workspace: Path) -> dict[str, Any]:
    try:
        payload = load_recipe(path)
    except RecipeError as error:
        return {"file": str(path), "id": None, "valid": False, "errors": [str(error)]}
    errors = validate_recipe(payload, workspace)
    return {
        "file": str(path),
        "id": payload.get("id"),
        "valid": not errors,
        "errors": errors,
    }


def run_recipe(path: Path, workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    payload = load_recipe(path)
    errors = validate_recipe(payload, workspace)
    if errors:
        raise RecipeError("; ".join(errors))

    limits = payload["limits"]
    settings = replace(
        Settings.from_env(),
        workspace_root=str(workspace),
        approval_mode="inspect",
        allow_network=False,
        auth_token=secrets.token_urlsafe(32),
        command_timeout=float(limits["timeout_seconds"]),
        max_output_bytes=int(limits["max_output_bytes"]),
        audit_log="",
    )
    server = MCPServer(settings, EventBus())
    session_id = server.create_session()["session_id"]
    receipts: list[dict[str, Any]] = []
    try:
        for step in payload["steps"]:
            planned = server.call_tool(
                "terminal_plan",
                {
                    "session_id": session_id,
                    "command": step["command"],
                    **({"cwd": step["cwd"]} if step.get("cwd") else {}),
                },
            )["structuredContent"]
            if planned["status"] != "planned":
                raise RecipeError(f"step {step['name']} did not produce an executable plan")
            executed = server.call_tool(
                "terminal_execute",
                {"session_id": session_id, "plan_id": planned["id"]},
            )
            receipt = executed["structuredContent"]
            receipts.append(receipt)
            expected_status = step["expected_status"]
            if receipt.get("status") != expected_status:
                raise RecipeError(
                    f"step {step['name']} returned {receipt.get('status')}, "
                    f"expected {expected_status}"
                )
    finally:
        server.close_session(session_id)

    return {
        "schema_version": "1.0",
        "recipe_id": payload["id"],
        "status": "succeeded",
        "workspace": str(workspace),
        "steps": [
            {
                "name": step["name"],
                "status": receipt["status"],
                "risk": receipt["risk"],
                "duration_ms": receipt["duration_ms"],
                "exit_code": receipt["exit_code"],
                "output_bytes": len(receipt["stdout"].encode("utf-8"))
                + len(receipt["stderr"].encode("utf-8")),
            }
            for step, receipt in zip(payload["steps"], receipts, strict=True)
        ],
        "receipts": receipts,
    }


__all__ = [
    "RecipeError",
    "load_recipe",
    "recipe_schema",
    "run_recipe",
    "validate_recipe",
    "validate_recipe_file",
]
