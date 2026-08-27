# ADR 0001: Deterministic execution boundary

- Status: accepted
- Date: 2026-08-27

## Context

Model text, HTTP handlers, STDIO messages, and web actions all need terminal results without creating separate trust paths.

## Decision

All commands pass through a versioned plan, deterministic `CommandPolicy`, explicit approval when required, session-scoped `ExecutionService`, bounded process group, and signed receipt. Model output is advisory and never directly executable.

## Consequences

New tools and recipes reuse the same engine. Some convenient shell syntax and interpreter commands remain unsupported. Wider host isolation still requires a disposable container or VM.
