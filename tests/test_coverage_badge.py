from scripts.check_coverage_badge import expected_badge


def test_coverage_badge_uses_factual_precision_and_thresholds():
    assert expected_badge(90.0) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": "90.00%",
        "color": "brightgreen",
    }
    assert expected_badge(84.891) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": "84.89%",
        "color": "green",
    }
