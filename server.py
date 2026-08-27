"""Compatibility entrypoint for the single application factory."""

from term_mcp_deepseek.app import create_app

app = create_app()

if __name__ == "__main__":
    from term_mcp_deepseek.cli import main

    raise SystemExit(main(["serve"]))
