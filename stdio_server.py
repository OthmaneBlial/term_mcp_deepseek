"""Compatibility entrypoint for the STDIO transport."""

from term_mcp_deepseek.stdio import run_stdio

if __name__ == "__main__":
    raise SystemExit(run_stdio())
