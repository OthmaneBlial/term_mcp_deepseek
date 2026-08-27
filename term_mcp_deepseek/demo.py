"""Model-free demonstration scenarios shared by the CLI and web UI."""

DEMO_SCENARIOS = [
    {
        "id": "inspect-workspace",
        "label": "Inspect workspace",
        "command": "pwd",
        "outcome": "A low-risk successful receipt",
    },
    {
        "id": "approval-cancel",
        "label": "Approval + cancel",
        "command": "sleep 15",
        "outcome": "Approve, pause, resume, then cancel a bounded process",
    },
    {
        "id": "catalog-overview",
        "label": "List top-level files",
        "command": "ls -la",
        "outcome": "Read-only output without a model key",
    },
]

__all__ = ["DEMO_SCENARIOS"]
