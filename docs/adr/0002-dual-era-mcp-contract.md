# ADR 0002: Dual-era MCP contract

- Status: accepted
- Date: 2026-08-27

## Context

Current clients use the modern discovery contract while existing clients still initialize through the legacy lifecycle.

## Decision

Target MCP `2026-07-28`, retain tested `2025-11-25` initialization compatibility, and share one dispatcher across STDIO and Streamable HTTP. Compatibility APIs remain documented separately from MCP transport behavior.

## Consequences

Every protocol change needs modern and legacy fixtures. Client evidence is dated, and unsupported combinations are reported instead of inferred.
