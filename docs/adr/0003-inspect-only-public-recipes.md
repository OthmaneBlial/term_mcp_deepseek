# ADR 0003: Inspect-only public recipes

- Status: accepted
- Date: 2026-08-27

## Context

Community examples can become copy-paste execution paths. A broad recipe format would make review and safe automation difficult.

## Decision

Repository recipes are schema-versioned, low-risk, inspect-only, network-free, write-free, and bounded. Validation runs each step through the production command policy; execution runs through the normal plan and receipt engine.

## Consequences

Recipes are easy to review and execute in CI. Workflows needing writes, project code, or network access remain explicit product actions rather than accepted public recipes.
