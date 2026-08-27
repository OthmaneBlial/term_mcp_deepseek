# Term MCP DeepSeek

[![CI](https://github.com/OthmaneBlial/term_mcp_deepseek/actions/workflows/ci.yml/badge.svg)](https://github.com/OthmaneBlial/term_mcp_deepseek/actions/workflows/ci.yml)
[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/OthmaneBlial/term_mcp_deepseek)](https://archestra.ai/mcp-catalog/othmaneblial__term_mcp_deepseek)

A local terminal copilot powered by DeepSeek, with one shared JSON-RPC dispatcher for HTTP and STDIO clients.

The repository is moving from a proof of concept toward a safe, inspectable MCP server. The current 0.9 line is for local development only: do not expose it to an untrusted network until the security phase in the roadmap is complete.

## Quick start

Requirements: Python 3.10 or newer and Bash.

    git clone https://github.com/OthmaneBlial/term_mcp_deepseek.git
    cd term_mcp_deepseek
    cp .env.example .env
    ./startup.sh

The server listens on http://127.0.0.1:8000 by default.

The DeepSeek key is optional for health checks, tool discovery, STDIO and local protocol tests. Add DEEPSEEK_API_KEY to ".env" only when using chat.

## One CLI

    term-mcp serve
    term-mcp stdio
    term-mcp doctor
    term-mcp version

The compatibility files "server.py" and "stdio_server.py" delegate to this CLI; they do not contain separate server implementations.

## HTTP contract

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Readiness and package version |
| GET | / | Local chat interface |
| POST | /chat | DeepSeek chat bridge |
| GET | /mcp/info | Declared capabilities |
| POST | /mcp | JSON-RPC dispatcher |
| GET | /stream?session_id=... | SSE session events |

Example tool discovery:

    curl http://127.0.0.1:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

## STDIO contract

STDOUT contains JSON-RPC responses only; diagnostics are written to STDERR.

    printf '%s\n' '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
      | python -m term_mcp_deepseek stdio

HTTP and STDIO use the same dispatcher and business methods.

## Docker

    docker compose up --build

The container and health check use port 8000. The repository is mounted read-write at "/workspace" in the development compose profile.

## Development

    ./local_ci.sh

The local CI command installs the project with development dependencies, checks formatting and lint, then runs the complete test suite with measured coverage.

## Project direction

The full, dependency-ordered plan is in [ROADMAP.md](ROADMAP.md). The central product flow is:

    plan → risk analysis → approval → bounded execution → receipt

Security limits are documented honestly as they are implemented. A passing syntax check or a decorative badge is not treated as proof of protocol compatibility or production readiness.

## License

MIT. See [LICENSE](LICENSE).
