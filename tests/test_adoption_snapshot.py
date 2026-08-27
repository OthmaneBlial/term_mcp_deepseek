from scripts.adoption_snapshot import main, summarize


def test_snapshot_keeps_unavailable_metrics_distinct_from_zero():
    snapshot = summarize(
        "owner/repo",
        release=None,
        contributors=None,
        onboarding_issues=[],
        reuse_issues=None,
        workflow_runs={"workflow_runs": []},
        recipe_count=5,
        errors={"release": "unavailable"},
    )

    metrics = snapshot["metrics"]
    assert metrics["release_asset_downloads"] is None
    assert metrics["contributors_returned_max_100"] is None
    assert metrics["open_onboarding_issues"] == 0
    assert metrics["opt_in_example_reuse_reports"] is None
    assert metrics["latest_ci_conclusion"] is None
    assert snapshot["privacy"]["product_telemetry"] is False


def test_snapshot_summarizes_only_public_evidence():
    snapshot = summarize(
        "owner/repo",
        release={
            "tag_name": "v1.0.0",
            "assets": [{"download_count": 4}, {"download_count": 7}],
        },
        contributors=[{"login": "one"}, {"login": "two"}],
        onboarding_issues=[{"number": 1}, {"number": 2, "pull_request": {}}],
        reuse_issues=[{"number": 3}],
        workflow_runs={"workflow_runs": [{"conclusion": "success"}]},
        recipe_count=5,
    )

    assert snapshot["metrics"] == {
        "latest_release": "v1.0.0",
        "release_asset_downloads": 11,
        "contributors_returned_max_100": 2,
        "open_onboarding_issues": 1,
        "opt_in_example_reuse_reports": 1,
        "public_recipe_count": 5,
        "latest_ci_conclusion": "success",
    }


def test_snapshot_cli_rejects_invalid_repository(capsys):
    try:
        main(["missing-owner"])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("invalid repository was accepted")

    assert "owner/name" in capsys.readouterr().err
