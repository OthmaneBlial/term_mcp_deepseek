# Contributing

Thank you for improving Term MCP DeepSeek. The easiest contributions to review are small, reproducible, and explicit about security boundaries.

## Setup

```bash
git clone https://github.com/OthmaneBlial/term_mcp_deepseek.git
cd term_mcp_deepseek
python3 -m venv .venv
.venv/bin/python -m pip install --editable ".[dev]"
./local_ci.sh
```

Supported development hosts are Linux and macOS with Python 3.10–3.13. Docker is useful for the packaged Linux path.

## Repository guide

- `term_mcp_deepseek/`: package, policy, execution, protocol, receipts, UI assets;
- `api/`: HTTP routes;
- `models/`: session event bus;
- `tools/`: JSON-RPC, auth, and DeepSeek adapter;
- `tests/`: unit, integration, protocol fixture, official-client, UI contract tests;
- `docs/`: architecture, compatibility, security, operations, and release guidance;
- `examples/`: small no-secret recipes checked in CI.

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing execution or protocol behavior.

## Quality gate

```bash
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest
```

Changes to policy, paths, process control, sessions, protocol metadata, auth, or receipts need a regression test. Changes to the web console need keyboard and narrow-viewport verification with no console errors.

## Security rules for changes

- Never execute model text directly.
- Never add a shell fallback.
- Keep policy default-deny and workspace-scoped.
- Do not weaken auth, origin, size, rate, timeout, or process limits for convenience.
- Never place real secrets, private paths, or private output in fixtures.
- Use a redacted receipt in issues and PRs.
- Treat confirm/trusted development commands as host code execution, not sandboxing.

Vulnerabilities must use GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md).

## Pull requests

1. Keep one coherent change per PR.
2. Explain the user-visible result and trust-boundary impact.
3. Add or update tests and documentation.
4. Run the complete quality gate.
5. Include actual validation output, not only expected results.
6. Do not include generated environments, build folders, logs, tokens, or unredacted receipts.

The PR template asks for protocol, security, and receipt impact so reviewers can find sensitive changes quickly.

## Adding a tool

A new tool must have:

- a strict input schema with `additionalProperties: false`;
- explicit annotations and a narrow description;
- argument validation in the shared server;
- a policy decision before any side effect;
- session ownership for mutable state;
- bounded execution and a final receipt when it runs a process;
- modern and legacy transport tests;
- failure tests proving that malformed or cross-session calls remain closed.

Do not add a direct terminal-write or arbitrary-shell tool.

## Commit style

Use a short imperative subject, for example:

```text
feat: add receipt replay recipe
fix: reject symlink escape in resource reads
docs: record inspector compatibility
test: cover cancellation after pause
```
