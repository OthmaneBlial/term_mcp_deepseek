# Maintainer playbook

## Issue response

Triage starts from a minimal reproduction, not a proposed patch. Confirm the reported version, transport, OS/Python, approval mode, smallest safe request, observed structured error, and redacted receipt. Reproduce in a temporary workspace before changing policy or protocol behavior.

Classify the report with one primary area label and one contribution label when useful. Security-boundary reports move to private vulnerability reporting. A critical confirmed bug must gain a regression test before the fix is considered complete.

## Architectural decisions

Record a short ADR under `docs/adr/` when a change alters:

- the execution or approval boundary;
- supported MCP versions or transports;
- receipt compatibility;
- workspace, process, or network isolation;
- the public recipe contract;
- packaging or release provenance.

ADRs contain context, decision, consequences, and status. Supersede old decisions instead of rewriting their history.

## Evidence in reviews

Ask for the command and result of relevant tests, not “tests should pass.” Separate local checks, CI checks, browser/device QA, and public release verification. Never ask a reporter to publish a token, private path, prompt, or unredacted terminal output.
