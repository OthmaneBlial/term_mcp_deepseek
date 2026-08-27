#!/usr/bin/env python3
"""Fail when the committed coverage badge differs from a pytest-cov JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def expected_badge(percent: float) -> dict[str, object]:
    if percent >= 90:
        color = "brightgreen"
    elif percent >= 80:
        color = "green"
    elif percent >= 70:
        color = "yellowgreen"
    else:
        color = "yellow"
    return {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{percent:.2f}%",
        "color": color,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("badge", type=Path)
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    actual = json.loads(args.badge.read_text(encoding="utf-8"))
    expected = expected_badge(float(report["totals"]["percent_covered"]))
    if actual != expected:
        raise SystemExit(f"coverage badge is stale: expected {json.dumps(expected)}")
    print(f"coverage badge: verified {actual['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
