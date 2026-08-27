# Three concrete demos

Each demo starts from a clone, needs no API key, and runs through the same policy and receipt path as MCP clients. Read the recipe JSON before execution; the declared permissions are part of its contract.

## Understand an unfamiliar repository

```bash
term-mcp recipe validate examples/recipes/inspect-repository.json --workspace /path/to/repo
term-mcp recipe run examples/recipes/inspect-repository.json --workspace /path/to/repo
```

Result: bounded receipts for the workspace location, top-level inventory, and Git state. This maps the repository surface; it does not execute or assess project code.

## Find the test surface before diagnosing a failure

```bash
term-mcp recipe run examples/recipes/diagnose-tests.json --workspace /path/to/repo
```

Result: receipts identify common test configuration and test files. The recipe intentionally does not run an unknown test suite. After review, a maintainer can add a project-specific command under `confirm` mode and the normal approval boundary.

## Inventory evidence for a local incident

```bash
term-mcp recipe run examples/recipes/analyze-logs.json --workspace /path/to/repo
term-mcp recipe run examples/recipes/verify-port-config.json --workspace /path/to/repo
```

Result: a bounded inventory of local log files and service-port declarations, without network access or mutation. The output may contain private filenames; use the web UI or `POST /receipts/redact` before sharing a receipt.

For the interactive plan → approval → execution → receipt flow, run `term-mcp serve` and use the built-in **Cancellation and receipt** scenario. The expected browser result is shown in the [README screenshot](../README.md#first-result-in-60-seconds).
