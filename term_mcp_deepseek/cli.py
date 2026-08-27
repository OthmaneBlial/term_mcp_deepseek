"""Command-line interface for all supported transports."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import requests

from models.event_bus import EventBus
from term_mcp_deepseek import __version__
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.demo import DEMO_SCENARIOS
from term_mcp_deepseek.receipts import receipt_report, receipt_summary
from term_mcp_deepseek.server import MCPServer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="term-mcp",
        description="Local, inspectable terminal tools for DeepSeek and MCP clients.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="Start the HTTP server")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--debug", action="store_true")

    subparsers.add_parser("stdio", help="Start the JSON-RPC STDIO transport")

    doctor = subparsers.add_parser("doctor", help="Check the local environment")
    doctor.add_argument("--json", action="store_true", dest="json_output")
    doctor.add_argument(
        "--connectivity",
        action="store_true",
        help="Also verify the configured DeepSeek endpoint without sending a prompt",
    )

    subparsers.add_parser("version", help="Print the installed version")
    subparsers.add_parser("token", help="Generate a strong local bearer token")
    demo = subparsers.add_parser("demo", help="List model-free demonstration scenarios")
    demo.add_argument("--json", action="store_true", dest="json_output")

    receipt = subparsers.add_parser("receipt", help="Inspect an exported execution receipt")
    receipt_commands = receipt.add_subparsers(dest="receipt_command", required=True)
    receipt_validate = receipt_commands.add_parser("validate", help="Validate schema and signature")
    receipt_validate.add_argument("file", type=Path)
    receipt_validate.add_argument("--structure-only", action="store_true")
    receipt_show = receipt_commands.add_parser("show", help="Print a privacy-aware receipt summary")
    receipt_show.add_argument("file", type=Path)
    return parser


def _doctor(
    settings: Settings,
    *,
    check_connectivity: bool = False,
) -> tuple[dict[str, object], bool]:
    workspace = Path(settings.workspace_root)
    configuration_errors = settings.validate_for_http()
    transport_ok, transport_detail = _check_stdio_transport(settings)
    checks = {
        "python": {
            "ok": sys.version_info >= (3, 10),
            "detail": sys.version.split()[0],
        },
        "bash": {
            "ok": shutil.which("bash") is not None,
            "detail": shutil.which("bash") or "not found",
        },
        "workspace_read": {
            "ok": workspace.is_dir() and os.access(workspace, os.R_OK),
            "detail": str(workspace),
        },
        "workspace_write": {
            "ok": workspace.is_dir() and os.access(workspace, os.W_OK),
            "detail": (
                "available"
                if workspace.is_dir() and os.access(workspace, os.W_OK)
                else "not available"
            ),
            "required": settings.approval_mode != "inspect",
        },
        "configuration": {
            "ok": not configuration_errors,
            "detail": "; ".join(configuration_errors) if configuration_errors else "valid",
        },
        "stdio_transport": {
            "ok": transport_ok,
            "detail": transport_detail,
        },
        "deepseek_key": {
            "ok": bool(settings.deepseek_api_key),
            "detail": "configured" if settings.deepseek_api_key else "optional; not configured",
            "required": False,
        },
        "auth_token": {
            "ok": len(settings.auth_token) >= 32,
            "detail": "configured" if settings.auth_token else "not configured",
        },
    }
    if check_connectivity:
        checks["deepseek_connectivity"] = _check_deepseek_connectivity(settings)
    required_ok = all(bool(check["ok"]) for check in checks.values() if check.get("required", True))
    return {"version": __version__, "checks": checks, "ok": required_ok}, required_ok


def _check_stdio_transport(settings: Settings) -> tuple[bool, str]:
    try:
        server = MCPServer(settings, EventBus())
        discovery = server.discover()
        versions = ", ".join(discovery["supportedVersions"])
        server.execution.sessions.close_all()
    except (KeyError, OSError, ValueError) as error:
        return False, f"dispatcher unavailable ({type(error).__name__})"
    return True, f"dispatcher ready ({versions})"


def _check_deepseek_connectivity(settings: Settings) -> dict[str, object]:
    if not settings.deepseek_api_key:
        return {
            "ok": False,
            "detail": "skipped; DEEPSEEK_API_KEY is not configured",
            "required": False,
        }
    try:
        response = requests.get(
            f"{settings.deepseek_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            timeout=min(settings.deepseek_timeout, 10),
        )
        response.raise_for_status()
    except requests.RequestException:
        return {"ok": False, "detail": "endpoint unavailable or rejected credentials"}
    return {"ok": True, "detail": f"reachable (HTTP {response.status_code})"}


def _serve_http(app, *, host: str, port: int, debug: bool) -> None:
    if debug:
        app.run(host=host, port=port, debug=True)
        return
    from waitress import serve

    serve(
        app,
        host=host,
        port=port,
        threads=4,
        clear_untrusted_proxy_headers=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "serve"

    if command == "version":
        print(__version__)
        return 0
    if command == "token":
        print(secrets.token_urlsafe(32))
        return 0
    if command == "demo":
        if args.json_output:
            print(json.dumps({"scenarios": DEMO_SCENARIOS}, indent=2))
        else:
            for scenario in DEMO_SCENARIOS:
                print(f"{scenario['id']}: {scenario['command']} — {scenario['outcome']}")
        return 0

    settings = Settings.from_env()
    if command == "receipt":
        try:
            payload = json.loads(args.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"receipt error: {error}", file=sys.stderr)
            return 2
        report = receipt_report(payload, settings.auth_token)
        if args.receipt_command == "show":
            if not report["schema_valid"]:
                print(json.dumps(report, indent=2), file=sys.stderr)
                return 1
            print(json.dumps(receipt_summary(payload), indent=2, sort_keys=True))
            return 0
        print(json.dumps(report, indent=2, sort_keys=True))
        valid = report["schema_valid"] and (bool(args.structure_only) or report["signature_valid"])
        return 0 if valid else 1
    if command == "doctor":
        report, ok = _doctor(settings, check_connectivity=args.connectivity)
        if args.json_output:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            for name, check in report["checks"].items():
                marker = "ok" if check["ok"] else "missing"
                print(f"{name}: {marker} ({check['detail']})")
        return 0 if ok else 1

    if command == "stdio":
        from term_mcp_deepseek.stdio import run_stdio

        return run_stdio(settings)

    from term_mcp_deepseek.app import create_app

    if not settings.auth_token:
        generated_token = secrets.token_urlsafe(32)
        settings = replace(settings, auth_token=generated_token)
        print(
            "Generated one-time AUTH_TOKEN (save it before sharing this terminal):",
            file=sys.stderr,
        )
        print(generated_token, file=sys.stderr)

    validation_errors = settings.validate_for_http()
    if validation_errors:
        for error in validation_errors:
            print(f"configuration error: {error}", file=sys.stderr)
        print("run 'term-mcp token' to generate a replacement AUTH_TOKEN", file=sys.stderr)
        return 2

    host = getattr(args, "host", None) or settings.host
    port = getattr(args, "port", None) or settings.port
    debug = bool(getattr(args, "debug", False) or settings.debug)
    app = create_app(settings=settings)
    try:
        _serve_http(app, host=host, port=port, debug=debug)
    finally:
        app.close_term_mcp()
    return 0


__all__ = ["main"]
