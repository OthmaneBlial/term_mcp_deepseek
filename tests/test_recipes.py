import json
from pathlib import Path

from term_mcp_deepseek.cli import main
from term_mcp_deepseek.recipes import load_recipe, run_recipe, validate_recipe

RECIPE_ROOT = Path(__file__).parents[1] / "examples" / "recipes"


def test_all_public_recipes_are_strict_and_safe():
    paths = sorted(RECIPE_ROOT.glob("*.json"))

    assert len(paths) == 5
    assert all(validate_recipe(load_recipe(path), Path.cwd()) == [] for path in paths)


def test_recipe_runs_through_normal_plan_and_receipt_engine(tmp_path):
    (tmp_path / ".env.example").write_text("PORT=8000\n", encoding="utf-8")
    result = run_recipe(RECIPE_ROOT / "read-only-boundary.json", tmp_path)

    assert result["status"] == "succeeded"
    assert all(step["risk"] == "low" for step in result["steps"])
    assert all(receipt["signature"] for receipt in result["receipts"])
    assert all(receipt["policy"]["allowed"] for receipt in result["receipts"])


def test_recipe_cli_reports_validation_errors(tmp_path, capsys):
    invalid = {
        "schema_version": "1.0",
        "id": "unsafe",
        "permissions": {"mode": "inspect", "network": False, "writes": False},
    }
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")

    assert main(["recipe", "validate", str(path), "--workspace", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["recipes"][0]["valid"] is False
