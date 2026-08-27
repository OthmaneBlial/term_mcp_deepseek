# Changelog

All notable changes are documented here. The project follows [Semantic Versioning](https://semver.org/) and keeps receipt schemas independently versioned.

## [Unreleased]

### Added

- Inspect-only community recipes, a versioned recipe schema and runner, a no-model benchmark, contributor documentation, safe public challenges, and architecture decisions.
- A proof gallery with CI-verified sharing-redacted receipts for success, cancellation, and timeout states.
- Reproducible unknown-repository, test-surface, and local-incident demos.
- A public adoption snapshot based on GitHub evidence, with no product telemetry.
- Dedicated onboarding and opt-in example-reuse issue paths plus categorized contributor-aware release notes.

### Changed

- Linked each MCP compatibility claim to executable tests, pinned commands, configuration, or an explicitly open verification issue.
- Added factual CI, coverage, security, release-asset, version, and MCP compatibility badges; CI rejects a stale coverage badge.

## [0.10.0] - 2026-08-27

### Added

- Approval-first browser mission control with responsive, keyboard-accessible, local-only assets.
- Versioned plans with policy reasons, risk, workspace, network, touched-file preview, and hard limits.
- Pause, resume, cancel, controlled retry, command copy, and live session-scoped events.
- Signed receipt schema, CLI validation/summary, import, full local copy, and redacted re-signed export.
- No-key guided demos and explicit DeepSeek-unavailable behavior.
- Modern MCP `2026-07-28` plus legacy `2025-11-25` client compatibility.
- Official MCP SDK and MCP Inspector interoperability evidence.
- Waitress production serving, packaged UI/schema assets, clean-wheel tests, and a pinned multi-stage non-root Docker image.
- Architecture, operations, feature, security, contribution, and release documentation.

### Changed

- Unified all transports behind one typed configuration, JSON-RPC dispatcher, and MCP server.
- Replaced implicit `CMD:` execution with plan/approve/execute tools.
- Replaced shared terminal state with isolated sessions and bounded subprocess groups.
- Made inspect mode and network denial the safe defaults.

### Security

- Added strong bearer authentication, exact origin allowlists, rate/request limits, path and symlink confinement, executable/capability allowlists, shell-composition denial, secret redaction, signed receipts, and an explicit threat model.

## [0.9.0] - 2026-08-27

Initial local beta before the approval-first architecture and production packaging work.

[Unreleased]: https://github.com/OthmaneBlial/term_mcp_deepseek/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/OthmaneBlial/term_mcp_deepseek/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/OthmaneBlial/term_mcp_deepseek/releases/tag/v0.9.0
