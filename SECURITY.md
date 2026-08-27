# Security policy

## Supported versions

Security fixes are applied to the latest release on the main branch.

| Version | Supported |
| --- | --- |
| 0.10.x | Yes |
| 0.9.x and older | No |

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose files, credentials, command execution or another user’s session. Use GitHub private vulnerability reporting for this repository and include:

- the affected version and transport;
- the configured approval mode;
- a minimal reproduction;
- the expected and observed security boundary;
- a redacted receipt when one exists.

Do not include real API keys, bearer tokens, private file contents or personal data.

## Operational requirements

- `term-mcp serve` creates and prints a strong ephemeral token when AUTH_TOKEN is absent; an explicitly configured token shorter than 32 characters is refused.
- Keep APPROVAL_MODE set to "inspect" unless the wider command surface is understood.
- Keep ALLOW_NETWORK false unless a specific approved workflow needs dependency access.
- Set WORKSPACE_ROOT to the smallest directory needed for the task.
- Do not add a wildcard to ALLOWED_ORIGINS.
- Do not enable TRUST_PROXY unless a trusted reverse proxy rewrites forwarding headers.
- Mount a disposable workspace when testing unfamiliar repositories.

## Security guarantees and limits

The default inspect mode parses commands without a shell, blocks interpreters and network clients, validates explicit paths against WORKSPACE_ROOT, rejects symlink escapes and emits signed redacted receipts.

Confirm and trusted modes intentionally permit project-defined development commands. Build tools and test runners can execute repository code, so those modes are not an operating-system sandbox. Run untrusted projects inside a disposable container or virtual machine.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the complete boundary and residual risks.
