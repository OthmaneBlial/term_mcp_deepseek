import json
from pathlib import Path

from term_mcp_deepseek.receipts import validate_receipt, verify_receipt_signature

ROOT = Path(__file__).parents[1]
GALLERY_FIXTURE_KEY = "gallery-fixture-signing-key-not-for-production"
REDACTED = "[REDACTED FOR SHARING]"


def test_gallery_receipts_are_valid_signed_and_private():
    receipt_paths = sorted((ROOT / "examples" / "receipts").glob("*.json"))

    assert len(receipt_paths) == 3
    assert {json.loads(path.read_text(encoding="utf-8"))["status"] for path in receipt_paths} == {
        "succeeded",
        "cancelled",
        "timed_out",
    }

    for path in receipt_paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        assert validate_receipt(receipt) == []
        assert verify_receipt_signature(receipt, GALLERY_FIXTURE_KEY) is True
        assert receipt["sharing_redacted"] is True
        assert receipt["command"] == REDACTED
        assert receipt["cwd"] == REDACTED
        assert receipt["stdout"] == REDACTED
        assert receipt["stderr"] == REDACTED
        assert receipt["policy"]["argv"] == []


def test_gallery_document_links_every_public_artifact():
    gallery = (ROOT / "docs" / "GALLERY.md").read_text(encoding="utf-8")

    for path in (ROOT / "examples" / "receipts").glob("*.json"):
        assert f"../examples/receipts/{path.name}" in gallery
    for path in (ROOT / "examples" / "recipes").glob("*.json"):
        assert f"../examples/recipes/{path.name}" in gallery
