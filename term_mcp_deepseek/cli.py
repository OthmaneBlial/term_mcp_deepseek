"""Command-line interface for all supported transports."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from term_mcp_deepseek import __version__
from term_mcp_deepseek.config import Settings


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

    subparsers.add_parser("version", help="Print the installed version")
    return parser


def _doctor(settings: Settings) -> tuple[dict[str, object], bool]:
    workspace = Path(settings.workspace_root)
    checks = {
        "python": {
            "ok": sys.version_info >= (3, 10),
            "detail": sys.version.split()[0],
        },
        "bash": {
            "ok": shutil.which("bash") is not None,
            "detail": shutil.which("bash") or "not found",
        },
        "workspace": {
            "ok": workspace.is_dir() and os.access(workspace, os.R_OK | os.W_OK),
            "detail": str(workspace),
        },
        "deepseek_key": {
            "ok": bool(settings.deepseek_api_key),
            "detail": "configured" if settings.deepseek_api_key else "optional; not configured",
            "required": False,
        },
    }
    required_ok = all(bool(check["ok"]) for check in checks.values() if check.get("required", True))
    return {"version": __version__, "checks": checks, "ok": required_ok}, required_ok


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "serve"

    if command == "version":
        print(__version__)
        return 0

    settings = Settings.from_env()
    if command == "doctor":
        report, ok = _doctor(settings)
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

    host = args.host or settings.host
    port = args.port or settings.port
    debug = bool(args.debug or settings.debug)
    app = create_app(settings=settings)
    app.run(host=host, port=port, debug=debug)
    return 0


__all__ = ["main"]
