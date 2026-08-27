#!/usr/bin/env python3
"""Measure local planning, events, receipts, output, and cancellation without a model."""

from __future__ import annotations

import argparse
import json
import queue
import statistics
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path

from models.event_bus import EventBus
from term_mcp_deepseek import __version__
from term_mcp_deepseek.config import Settings
from term_mcp_deepseek.server import MCPServer

BENCHMARK_TOKEN = "benchmark-token-that-is-longer-than-thirty-two-characters"


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = max(0, min(len(ordered) - 1, round(0.95 * (len(ordered) - 1))))
    return {
        "min": round(ordered[0], 3),
        "median": round(statistics.median(ordered), 3),
        "p95": round(ordered[p95_index], 3),
        "max": round(ordered[-1], 3),
    }


def _settings(workspace: Path, *, mode: str, timeout: float) -> Settings:
    return replace(
        Settings.from_env(),
        workspace_root=str(workspace.resolve()),
        approval_mode=mode,
        allow_network=False,
        auth_token=BENCHMARK_TOKEN,
        command_timeout=timeout,
        max_output_bytes=65_536,
        audit_log="",
    )


def _execute_plan(
    server: MCPServer,
    session_id: str,
    plan_id: str,
    result: dict[str, object],
) -> None:
    result.update(
        server.call_tool(
            "terminal_execute",
            {"session_id": session_id, "plan_id": plan_id},
        )["structuredContent"]
    )


def run_benchmark(iterations: int = 5, workspace: Path | None = None) -> dict[str, object]:
    if iterations < 1 or iterations > 100:
        raise ValueError("iterations must be between 1 and 100")

    temporary = tempfile.TemporaryDirectory() if workspace is None else None
    selected_workspace = Path(temporary.name) if temporary else workspace
    assert selected_workspace is not None

    event_bus = EventBus()
    server = MCPServer(_settings(selected_workspace, mode="inspect", timeout=5), event_bus)
    plan_latencies: list[float] = []
    first_event_latencies: list[float] = []
    execution_latencies: list[float] = []
    output_sizes: list[int] = []
    try:
        for _ in range(iterations):
            session_id = server.create_session()["session_id"]
            subscriber_id, events = event_bus.subscribe(session_id)
            started = time.perf_counter()
            plan = server.call_tool(
                "terminal_plan",
                {"session_id": session_id, "command": "pwd"},
            )["structuredContent"]
            planned_at = time.perf_counter()
            try:
                events.get(timeout=1)
            except queue.Empty as error:
                raise RuntimeError("plan event was not published") from error
            event_at = time.perf_counter()
            receipt = server.call_tool(
                "terminal_execute",
                {"session_id": session_id, "plan_id": plan["id"]},
            )["structuredContent"]
            finished = time.perf_counter()
            plan_latencies.append((planned_at - started) * 1000)
            first_event_latencies.append((event_at - started) * 1000)
            execution_latencies.append((finished - planned_at) * 1000)
            output_sizes.append(
                len(receipt["stdout"].encode("utf-8")) + len(receipt["stderr"].encode("utf-8"))
            )
            event_bus.unsubscribe(session_id, subscriber_id)
            server.close_session(session_id)
    finally:
        server.execution.sessions.close_all()

    cancellation_server = MCPServer(
        _settings(selected_workspace, mode="confirm", timeout=5), EventBus()
    )
    cancelled = 0
    try:
        for _ in range(iterations):
            session_id = cancellation_server.create_session()["session_id"]
            plan = cancellation_server.call_tool(
                "terminal_plan",
                {"session_id": session_id, "command": "sleep 5"},
            )["structuredContent"]
            cancellation_server.call_tool(
                "terminal_approve",
                {"session_id": session_id, "plan_id": plan["id"]},
            )
            result: dict[str, object] = {}

            worker = threading.Thread(
                target=_execute_plan,
                args=(cancellation_server, session_id, plan["id"], result),
                daemon=True,
            )
            worker.start()
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                session = cancellation_server.execution.sessions.get(session_id)
                if session.active_process is not None:
                    break
                time.sleep(0.005)
            cancellation_server.call_tool("terminal_cancel", {"session_id": session_id})
            worker.join(timeout=2)
            if worker.is_alive():
                raise RuntimeError("cancelled benchmark process did not stop")
            cancelled += int(result.get("status") == "cancelled")
            cancellation_server.close_session(session_id)
    finally:
        cancellation_server.execution.sessions.close_all()
        if temporary:
            temporary.cleanup()

    return {
        "schema_version": "1.0",
        "version": __version__,
        "iterations": iterations,
        "model": {
            "enabled": False,
            "cost_usd": None,
            "note": "No prompt or network request is made by this benchmark.",
        },
        "metrics": {
            "plan_latency_ms": _summary(plan_latencies),
            "time_to_first_event_ms": _summary(first_event_latencies),
            "execution_latency_ms": _summary(execution_latencies),
            "output_bytes": {
                "median": round(statistics.median(output_sizes), 3),
                "max": max(output_sizes),
            },
            "cancellation_rate": round(cancelled / iterations, 3),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args.iterations, args.workspace)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        return 1
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        metrics = report["metrics"]
        print(f"plan p95: {metrics['plan_latency_ms']['p95']} ms")
        print(f"first event p95: {metrics['time_to_first_event_ms']['p95']} ms")
        print(f"execution p95: {metrics['execution_latency_ms']['p95']} ms")
        print(f"cancellation rate: {metrics['cancellation_rate']:.0%}")
        print("model cost: not measured (model disabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
