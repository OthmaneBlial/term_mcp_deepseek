#!/usr/bin/env python3
"""Report public adoption evidence without collecting product telemetry."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.github.com"


def fetch_json(url: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "term-mcp-deepseek-adoption-snapshot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def summarize(
    repository: str,
    *,
    release: dict[str, Any] | None,
    contributors: list[dict[str, Any]] | None,
    onboarding_issues: list[dict[str, Any]] | None,
    reuse_issues: list[dict[str, Any]] | None,
    workflow_runs: dict[str, Any] | None,
    recipe_count: int,
    errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    assets = release.get("assets", []) if release else []
    runs = workflow_runs.get("workflow_runs", []) if workflow_runs else []

    def issue_count(items: list[dict[str, Any]] | None) -> int | None:
        if items is None:
            return None
        return sum("pull_request" not in item for item in items)

    return {
        "schema_version": "1.0",
        "repository": repository,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "product_telemetry": False,
            "command_or_receipt_collection": False,
        },
        "metrics": {
            "latest_release": release.get("tag_name") if release else None,
            "release_asset_downloads": (
                sum(int(asset.get("download_count", 0)) for asset in assets)
                if release is not None
                else None
            ),
            "contributors_returned_max_100": (
                len(contributors) if contributors is not None else None
            ),
            "open_onboarding_issues": issue_count(onboarding_issues),
            "opt_in_example_reuse_reports": issue_count(reuse_issues),
            "public_recipe_count": recipe_count,
            "latest_ci_conclusion": runs[0].get("conclusion") if runs else None,
        },
        "sources": {
            "release": f"{API_ROOT}/repos/{repository}/releases/latest",
            "contributors": f"{API_ROOT}/repos/{repository}/contributors?per_page=100",
            "onboarding": (
                f"{API_ROOT}/repos/{repository}/issues?state=open&labels=onboarding&per_page=100"
            ),
            "example_reuse": (
                f"{API_ROOT}/repos/{repository}/issues?state=all&labels=example%20reuse&per_page=100"
            ),
            "ci": (
                f"{API_ROOT}/repos/{repository}/actions/workflows/ci.yml/runs"
                "?branch=main&status=completed&per_page=1"
            ),
        },
        "errors": errors or {},
    }


def collect(repository: str, recipe_dir: Path, token: str | None) -> dict[str, Any]:
    urls = {
        "release": f"{API_ROOT}/repos/{repository}/releases/latest",
        "contributors": f"{API_ROOT}/repos/{repository}/contributors?per_page=100",
        "onboarding": (
            f"{API_ROOT}/repos/{repository}/issues?state=open&labels=onboarding&per_page=100"
        ),
        "example_reuse": (
            f"{API_ROOT}/repos/{repository}/issues?state=all&labels=example%20reuse&per_page=100"
        ),
        "ci": (
            f"{API_ROOT}/repos/{repository}/actions/workflows/ci.yml/runs"
            "?branch=main&status=completed&per_page=1"
        ),
    }
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, url in urls.items():
        try:
            values[name] = fetch_json(url, token)
        except (OSError, ValueError, urllib.error.HTTPError) as error:
            values[name] = None
            errors[name] = f"{type(error).__name__}: source unavailable"

    return summarize(
        repository,
        release=values["release"],
        contributors=values["contributors"],
        onboarding_issues=values["onboarding"],
        reuse_issues=values["example_reuse"],
        workflow_runs=values["ci"],
        recipe_count=len(list(recipe_dir.glob("*.json"))),
        errors=errors,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="GitHub owner/repository")
    parser.add_argument(
        "--recipe-dir",
        type=Path,
        default=Path(__file__).parents[1] / "examples" / "recipes",
    )
    args = parser.parse_args(argv)
    if args.repository.count("/") != 1:
        parser.error("repository must use owner/name")
    snapshot = collect(args.repository, args.recipe_dir, os.getenv("GITHUB_TOKEN"))
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
