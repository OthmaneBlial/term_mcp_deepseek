# Term MCP DeepSeek

[![CI](https://github.com/OthmaneBlial/term_mcp_deepseek/actions/workflows/ci.yml/badge.svg)](https://github.com/OthmaneBlial/term_mcp_deepseek/actions/workflows/ci.yml)
[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/OthmaneBlial/term_mcp_deepseek)](https://archestra.ai/mcp-catalog/othmaneblial__term_mcp_deepseek)

A local, approval-first terminal copilot powered by DeepSeek, with one dual-era MCP dispatcher for HTTP and STDIO clients.

The current 0.9 line targets MCP `2026-07-28` and keeps `2025-11-25` handshake compatibility. It is designed for localhost and repository-scoped workspaces; confirm/trusted mode is not an operating-system sandbox for untrusted code.

## Quick start

Requirements: Python 3.10 or newer and Bash.

    git clone https://github.com/OthmaneBlial/term_mcp_deepseek.git
    cd term_mcp_deepseek
    cp .env.example .env
    ./startup.sh token

Copy the generated value into AUTH_TOKEN in ".env", then start the server:

    ./startup.sh

The server listens on http://127.0.0.1:8000 by default.

AUTH_TOKEN must contain at least 32 characters when provided. If it is omitted, `term-mcp serve` generates a strong ephemeral token and prints it once at startup. The DeepSeek key is optional for health checks, tool discovery, STDIO and local protocol tests. Add DEEPSEEK_API_KEY to ".env" only when using chat.

## One CLI

    term-mcp serve
    term-mcp stdio
    term-mcp doctor
    term-mcp version
    term-mcp token

The compatibility files "server.py" and "stdio_server.py" delegate to this CLI; they do not contain separate server implementations.

## MCP compatibility

The full capability, transport, error, and tested-client matrix is in [docs/MCP_COMPATIBILITY.md](docs/MCP_COMPATIBILITY.md). The normal local integration is STDIO:

```json
{
  "mcpServers": {
    "term-mcp-deepseek": {
      "command": "/absolute/path/to/term_mcp_deepseek/.venv/bin/term-mcp",
      "args": ["stdio"],
      "env": {"WORKSPACE_ROOT": "/absolute/path/to/your/project"}
    }
  }
}
```

## HTTP and web contract

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Readiness and package version |
| GET | / | Local chat interface |
| POST | /mcp | Modern or legacy MCP Streamable HTTP in JSON response mode |
| DELETE | /mcp | Terminate a legacy MCP transport session |
| POST | /sessions | Create an isolated web execution session (deprecated compatibility API) |
| DELETE | /sessions/{id} | Close a session and cancel its process |
| POST | /chat | DeepSeek planning chat; never executes text |
| GET | /mcp/info | Declared capabilities and supported protocol versions |
| GET | /stream?session_id=... | Web execution events (deprecated compatibility API, not MCP transport SSE) |

Example tool discovery:

    curl http://127.0.0.1:8000/mcp \
      -H "Authorization: Bearer $AUTH_TOKEN" \
      -H "Accept: application/json, text/event-stream" \
      -H "Content-Type: application/json" \
      -H "MCP-Protocol-Version: 2026-07-28" \
      -H "Mcp-Method: server/discover" \
      -d '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"curl","version":"1"},"io.modelcontextprotocol/clientCapabilities":{}}}}'

## STDIO contract

STDOUT contains JSON-RPC responses only; diagnostics are written to STDERR.

    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"stdio-smoke","version":"1"},"io.modelcontextprotocol/clientCapabilities":{}}}}' \
      | python -m term_mcp_deepseek stdio

HTTP and STDIO use the same dispatcher and business methods. STDIO is authorized by the parent process and does not require the HTTP bearer token.

## Docker

    AUTH_TOKEN=replace-with-a-strong-token docker compose up --build

The container and health check use port 8000. The repository is mounted read-write at "/workspace" in the development compose profile.

## Development

    ./local_ci.sh

The local CI command installs the project with development dependencies, checks formatting and lint, then runs the complete test suite with measured coverage.

## Project direction

The full, dependency-ordered plan is in [ROADMAP.md](ROADMAP.md). The central product flow is:

    plan → risk analysis → approval → bounded execution → receipt

The current terminal flow never executes model text. Call `terminal_plan` first; it creates an execution session when one is not supplied. Use `terminal_approve` when required, then `terminal_execute`. Commands are parsed without a shell, constrained to the configured workspace, bounded by time and output limits, and recorded as signed redacted receipts.

## License

MIT. See [LICENSE](LICENSE).
