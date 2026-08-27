# Feature matrix

This matrix describes the current implementation, not planned behavior.

## Product capabilities

| Capability | Status | Boundary |
| --- | --- | --- |
| Versioned command plans | Supported | Schema `1.0`; session-bound |
| Human approval | Supported | Required according to mode and policy |
| Read-only inspect mode | Supported | Default; no shell and no project-code runners |
| Confirm mode | Supported | Wider surface; approval required for risky actions |
| Trusted mode | Supported | Pre-approved surface; still bounded and receipted |
| Pause/resume/cancel | Supported | POSIX process groups; macOS/Linux |
| Timeout/output/process limits | Supported | Configurable hard bounds; one active process per session |
| Live execution events | Supported | Session-scoped SSE compatibility API |
| Signed receipts | Supported | JSON Schema plus HMAC-SHA256 |
| Share-safe receipt export | Supported | Private command/path/argv/output removed and re-signed |
| Receipt CLI validation | Supported | Full signature or structure-only mode |
| DeepSeek advisor | Optional | Bounded retries, timeout, token budget; never execution |
| No-key demo | Supported | Discovery, local planning, sandbox, and receipts |
| Browser mission control | Supported | Keyboard, responsive layouts, no external CDN |
| Mandatory telemetry | Not present | Local operation does not report usage |
| Windows execution controls | Not supported | POSIX signal/process-group implementation |
| Remote multi-tenancy | Not supported | Designed for localhost and one trusted operator |
| Arbitrary shell syntax | Not supported | Pipes, redirects, expansion, substitution, and shells blocked |

## Protocol and transport

| Surface | Version/status | Evidence |
| --- | --- | --- |
| MCP modern | `2026-07-28` | Contract fixtures, official Python SDK, MCP Inspector |
| MCP legacy | `2025-11-25` | Initialize/session lifecycle tests, official Python SDK |
| STDIO | Supported | Shared dispatcher; stdout JSON only |
| Streamable HTTP | Supported | Bearer auth, origin allowlist, request limits |
| Web compatibility API | Supported, deprecated where marked | `/sessions`, `/stream`, `/chat` |

See [MCP_COMPATIBILITY.md](MCP_COMPATIBILITY.md) for the dated client matrix.

## Default limits

| Limit | Default |
| --- | --- |
| Session inactivity | 3,600 seconds |
| Concurrent execution sessions | 10 |
| Active processes per session | 1 |
| Command duration | 20 seconds |
| Command length | 1,000 characters |
| Combined output read limit per stream | 1 MiB |
| HTTP request body | 64 KiB |
| HTTP rate limit | 60 requests/minute/address |
| DeepSeek timeout | 20 seconds |
| DeepSeek retries | 2 after the first attempt |
| DeepSeek output budget | 1,024 tokens |

Environment overrides are documented in [OPERATIONS.md](OPERATIONS.md).
