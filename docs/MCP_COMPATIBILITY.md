# MCP compatibility

Term MCP DeepSeek is a dual-era MCP server. Its primary contract is the current stateless `2026-07-28` specification. It also supports the `2025-11-25` initialize handshake for established clients.

## Protocol targets

| Era | Version | Lifecycle | Status |
| --- | --- | --- | --- |
| Modern | `2026-07-28` | Per-request metadata; optional `server/discover`; no transport session | Primary, tested |
| Legacy | `2025-11-25` | `initialize` → `notifications/initialized`; optional `Mcp-Session-Id` | Compatibility, tested |

The implementation follows the official [versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning), [discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover), [STDIO](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio), [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http), and [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) contracts.

## Capabilities

| Capability | Supported | Notes |
| --- | --- | --- |
| Tools | Yes | Deterministic catalog; strict input schemas; text and structured results |
| Resources | Yes | UTF-8 files under `WORKSPACE_ROOT`; traversal and symlink escape rejected |
| Prompts | Yes | One safe terminal-planning prompt |
| Pagination | Yes | Cursor accepted; catalogs currently fit one deterministic page |
| Tool list notifications | No | Advertised as `listChanged: false` |
| Resource subscriptions | No | Advertised as `subscribe: false` |
| Sampling, elicitation, roots callback | No | Not advertised |
| Extensions and tasks | No | No extension is advertised |

## Transports

### STDIO

`term-mcp stdio` is the recommended local transport. It accepts one newline-delimited JSON-RPC message per line, writes protocol messages only to stdout, sends diagnostics to stderr, and exits on EOF. Modern discovery and the legacy initialize handshake use the same dispatcher.

### Streamable HTTP

`POST /mcp` is the only MCP message endpoint. HTTP requires bearer authentication, an allowed `Origin` when one is present, bounded request size, rate limiting, and matching MCP metadata headers.

- Modern requests are stateless and require the `2026-07-28` metadata and headers.
- Legacy initialize responses mint a cryptographically random `Mcp-Session-Id`; subsequent legacy requests must present it with `MCP-Protocol-Version: 2025-11-25`.
- Responses use JSON mode. Request-scoped protocol SSE and `subscriptions/listen` are not implemented; `GET /mcp` therefore returns 405.
- `DELETE /mcp` terminates a legacy transport session.

The execution session carried by terminal tools is an application handle, not an MCP transport session. `terminal_plan` creates it automatically when `session_id` is omitted.

## Error contract

| Condition | Result |
| --- | --- |
| Invalid JSON / request / params | JSON-RPC `-32700`, `-32600`, or `-32602` |
| Unsupported protocol version | JSON-RPC `-32022` with supported versions |
| Missing or mismatched modern HTTP header | HTTP 400/406 with JSON-RPC `-32020` |
| Unknown modern RPC method | HTTP 404 with JSON-RPC `-32601` |
| Unknown tool | JSON-RPC `-32602` |
| Policy denial, missing approval, timeout, cancellation | Valid `CallToolResult` with `isError: true` and structured, actionable data |
| Missing/invalid HTTP bearer token | HTTP 401 before protocol dispatch |

Errors never include Python tracebacks or model-provider response bodies.

## Compatibility API boundary

The following routes are web-product compatibility APIs, not MCP methods:

| Route | Purpose | Status |
| --- | --- | --- |
| `POST /sessions` | Create an execution session for the web UI | Deprecated compatibility API |
| `DELETE /sessions/{id}` | Close a web execution session | Deprecated compatibility API |
| `GET /stream?session_id=...` | Web UI execution-event SSE | Deprecated compatibility API |
| `POST /chat` | Optional DeepSeek planning chat | Deprecated compatibility API |
| `GET /health` | Public process health | Stable operational API |

Compatibility responses include `Deprecation`, `Sunset`, and documentation `Link` headers. The browser UI may use these routes until its MCP-native migration is complete.

## Client verification matrix

Verified on 2026-08-27 from the repository checkout, without a DeepSeek API key:

| Client | Version | STDIO modern | STDIO legacy | HTTP modern | HTTP legacy |
| --- | --- | --- | --- | --- | --- |
| Official MCP Python SDK | `2.1.1` | Tested | Tested | Tested | Tested |
| MCP Inspector CLI | `2.4.0` | Tested (`tools/list`, `tools/call`) | Negotiated by client | Not tested | Not tested |
| Claude Desktop / Claude Code | Not pinned | Not tested | Not tested | Not tested | Not tested |
| Codex | Not pinned | Not tested | Not tested | Not tested | Not tested |

“Not tested” is intentional evidence, not a compatibility claim. The executable Python SDK checks run in the normal test suite; the Inspector commands are documented below for manual release verification.

```bash
WORKSPACE_ROOT="$PWD" npx -y @modelcontextprotocol/inspector@2.4.0 \
  --cli ./startup.sh stdio --method tools/list --format json

WORKSPACE_ROOT="$PWD" npx -y @modelcontextprotocol/inspector@2.4.0 \
  --cli ./startup.sh stdio --method tools/call \
  --tool-name terminal_plan --tool-args-json '{"command":"pwd"}' --format json
```
