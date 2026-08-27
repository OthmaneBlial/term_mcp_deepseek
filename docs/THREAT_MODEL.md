# Threat model

## Assets

- files inside and outside the configured workspace;
- DeepSeek credentials and the local HTTP bearer token;
- command output, receipts and chat history;
- process availability and host resources;
- isolation between concurrent sessions.

## Trust boundaries

1. Model text is untrusted data. It is never interpreted as an execution instruction.
2. HTTP requests are untrusted until bearer authentication, origin checks, size limits and rate limits pass.
3. A terminal plan is untrusted until the command policy parses and classifies it.
4. Approval is a user decision, not proof that project code is safe.
5. STDIO is trusted only to the extent that the parent process and local user are trusted.

## Defenses

| Threat | Control |
| --- | --- |
| Prompt injection using "CMD:" | Model responses are text only; direct execution markers were removed |
| Shell injection | Commands use argument arrays with shell disabled; composition and expansion characters are rejected |
| Path traversal | Working directories and explicit path arguments resolve under WORKSPACE_ROOT |
| Symlink escape | Existing paths are resolved before policy approval; resource symlinks are refused |
| Destructive deletion | Broad workspace targets are always blocked; writes are blocked in inspect mode |
| Secret exfiltration | Interpreters and network clients are blocked; child environments exclude application secrets |
| Cross-session access | Plans, processes, receipts and cancellation are owned by one random session id |
| Unauthorized HTTP use | Strong bearer token required by default; sensitive routes fail closed |
| Cross-origin request | Explicit origin allowlist; wildcard origins are invalid configuration |
| Unbounded command | Timeout, process-group termination and output truncation |
| Output spoofing | stdout, stderr, exit code and final status remain separate fields in a signed receipt |
| Log leakage | Known credentials and labeled secrets are redacted before receipt persistence |
| Denial of service | Request size, rate, session count, timeout and output limits |

## Approval modes

### inspect

The default. Only allowlisted read-oriented commands run. No approval is required because the command surface is deliberately narrow.

### confirm

Workspace writes and project development commands can be planned, but each plan requires explicit approval. This mode may run code from the repository.

### trusted

Allowed write and development commands do not prompt after policy validation. Receipts remain mandatory. This mode is intended only for a pre-trusted workspace.

## Residual risks

- The policy layer is not a kernel or hypervisor boundary.
- Approved test runners, package managers and build systems may execute arbitrary repository code.
- A compromised local user can read the process environment or alter the repository.
- A bearer token protects the HTTP API but does not provide multi-user authorization or role separation.
- Receipt signatures prove integrity under the local signing token; they are not remote attestations.
- The read command allowlist must be reviewed whenever a new executable or option is added.

## Security regression requirements

Every fixed vulnerability must add a failing-before, passing-after test. At minimum, CI covers shell composition, interpreters, absolute and parent paths, symlinks, broad deletion, network dependency operations, approval enforcement, timeout, cancellation, output limits, session ownership, origin checks and missing authentication.
