# Operations

## Supported runtime

- Python 3.10–3.13
- Linux or macOS
- Localhost by default
- Waitress for normal HTTP serving; Flask only with `term-mcp serve --debug`

Windows is not currently supported for command execution because pause, resume, cancellation, and process isolation use POSIX process groups and signals.

## Configuration reference

All configuration comes from environment variables. `.env` is loaded for local convenience and must not be committed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | HTTP bind address |
| `PORT` | `8000` | HTTP port |
| `DEBUG` | `false` | Use Flask development server when true |
| `AUTH_TOKEN` | Generated for `serve` | HTTP bearer and receipt signing key; configured values need 32+ chars |
| `ALLOWED_ORIGINS` | localhost/127.0.0.1 on `8000` | Exact browser-origin allowlist; wildcard refused |
| `WORKSPACE_ROOT` | Current directory | Only filesystem scope exposed to policy/resources |
| `APPROVAL_MODE` | `inspect` | `inspect`, `confirm`, or `trusted` |
| `ALLOW_NETWORK` | `false` | Allow policy-recognized dependency network operations |
| `TRUST_PROXY` | `false` | Honor one trusted proxy hop through `ProxyFix` |
| `SESSION_TIMEOUT` | `3600` | Session inactivity expiry in seconds |
| `MAX_CONCURRENT_SESSIONS` | `10` | Execution-session cap |
| `COMMAND_TIMEOUT` | `20` | Per-command hard limit in seconds |
| `MAX_COMMAND_LENGTH` | `1000` | Input command length cap |
| `MAX_OUTPUT_BYTES` | `1048576` | Read cap for each output stream |
| `MAX_REQUEST_BYTES` | `65536` | HTTP body limit |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-address HTTP request cap |
| `AUDIT_LOG` | Empty | Optional append-only JSONL receipt path |
| `DEEPSEEK_API_KEY` | Empty | Optional advisor credential |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Advisor model |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | Advisor API root |
| `DEEPSEEK_TIMEOUT` | `20` | Advisor HTTP timeout |
| `DEEPSEEK_MAX_RETRIES` | `2` | Retries after the first attempt, maximum 5 |
| `DEEPSEEK_BACKOFF` | `0.25` | Initial exponential backoff seconds |
| `DEEPSEEK_MAX_TOKENS` | `1024` | Advisor output-token cap, maximum 8192 |
| `LOG_LEVEL` | `INFO` | Application log level |
| `LOG_FILE` | `logs/term_mcp_deepseek.log` | Local log destination |
| `LOG_MAX_BYTES` | `10485760` | Log rotation threshold |
| `LOG_BACKUP_COUNT` | `5` | Rotated file count |

When overriding `--port`, also include the resulting browser origin in `ALLOWED_ORIGINS`. The server intentionally does not infer trust from an arbitrary bind port.

## Preflight

```bash
export AUTH_TOKEN="$(term-mcp token)"
export WORKSPACE_ROOT="$PWD"
term-mcp doctor
```

`doctor` verifies Python, Bash, workspace read/write permissions, configuration, and the MCP dispatcher without requiring a model key or network. Add `--connectivity` to make an explicit, read-only request to the configured DeepSeek `/models` endpoint.

## Health and shutdown

`GET /health` is public and returns the package version. All other environment-reading routes require the bearer token.

Waitress handles `SIGTERM`/`Ctrl+C`; the CLI closes active execution sessions in `finally`, which terminates process groups and removes event queues. Give the process up to ten seconds to stop before escalating.

## Docker

The Dockerfile:

- pins the Dockerfile frontend and Python base by digest;
- pins the complete runtime dependency set through `constraints.txt`;
- builds all wheels in a networked builder stage;
- installs from local wheels only in the runtime stage;
- runs as UID/GID `10001`;
- has no compiler or package manager use at runtime;
- exposes a Python-only health check and a `SIGTERM` stop signal.

The compose configuration mounts the checkout read-only at `/workspace` and uses inspect mode. Create a separate writable disposable volume before using confirm/trusted mode in a container.

## Reverse proxy

Remote exposure is not a recommended default. If a trusted reverse proxy is necessary:

1. terminate TLS at the proxy;
2. set an exact HTTPS `ALLOWED_ORIGINS` value;
3. set `TRUST_PROXY=true` only when the application cannot be reached around that proxy;
4. keep bearer tokens in a secret manager;
5. restrict network access to known operators;
6. retain rate limits and request-size limits;
7. use a disposable workspace for untrusted code.

## Audit retention

`AUDIT_LOG` is opt-in. Each JSONL row contains one signed, secret-redacted receipt. The application does not rotate this audit file; use the host log/retention system and treat it as potentially sensitive because repository output can contain private data.

Use the UI’s **Export redacted** action before sharing a receipt outside the local trust boundary.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `AUTH_TOKEN must contain at least 32 characters` | Generate one with `term-mcp token` or omit it for an ephemeral serve token |
| `origin_not_allowed` | Add the exact scheme, host, and port to `ALLOWED_ORIGINS` |
| `unknown or expired session` | Start a new web session and rebuild the plan |
| Plan is blocked | Read `policy.reasons`; narrow the command/path or choose an explicitly appropriate mode |
| Advisor unavailable | Configure `DEEPSEEK_API_KEY`; local tools remain usable |
| UI or schema missing after install | Confirm the wheel contains `term_mcp_deepseek/static/` and `schemas/receipt.schema.json` |
| Docker container has no workspace writes | Expected with the read-only inspect compose mount |

## Upgrade and rollback

Release artifacts include a wheel, source archive, and `SHA256SUMS`. Verify the checksum, install the exact version in a clean environment, and keep the prior wheel until the new health/MCP smoke checks pass.

Rollback is reinstalling the previous wheel or redeploying the previous immutable image digest. Receipts are versioned independently; do not rewrite historical audit rows during an application rollback.

See [RELEASING.md](RELEASING.md) for the maintainer procedure.
