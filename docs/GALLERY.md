# Proof gallery

This gallery contains reproducible workflows and complete **sharing-redacted** receipts. It is evidence of bounded behavior, not a claim that model-generated commands are safe.

## Receipt states

| Outcome | What the artifact proves | Receipt |
| --- | --- | --- |
| Successful inspection | A low-risk, read-only command reached an unambiguous `succeeded` state. | [succeeded-inspection.json](../examples/receipts/succeeded-inspection.json) |
| User cancellation | An approved process was stopped and recorded with its termination signal. | [cancelled-process.json](../examples/receipts/cancelled-process.json) |
| Timeout | A process that exceeded its approved limit reached `timed_out`, not a generic failure. | [timed-out-process.json](../examples/receipts/timed-out-process.json) |

All three fixtures pass the public receipt schema and HMAC verifier in CI. Their fixture key is deliberately public and must never be used in a real deployment:

```text
gallery-fixture-signing-key-not-for-production
```

Reproduce validation from a clone:

```bash
AUTH_TOKEN=gallery-fixture-signing-key-not-for-production \
  term-mcp receipt validate examples/receipts/succeeded-inspection.json
```

The command, workspace, arguments, stdout, and stderr are absent from shared fixtures. The command digest remains so two holders of the original command can compare it without publishing the command. A receipt proves what this process recorded; it does not prove that the inspected repository or command was trustworthy.

## Safe recipe catalog

| Question | Reproduction | Permissions | Recipe |
| --- | --- | --- | --- |
| What is in this unfamiliar repository? | `term-mcp recipe run examples/recipes/inspect-repository.json --workspace .` | inspect, no network, no writes | [inspect-repository.json](../examples/recipes/inspect-repository.json) |
| Where are the tests and their configuration? | `term-mcp recipe run examples/recipes/diagnose-tests.json --workspace .` | inspect, no network, no writes | [diagnose-tests.json](../examples/recipes/diagnose-tests.json) |
| Which JavaScript or TypeScript test surfaces are present? | `term-mcp recipe run examples/recipes/discover-javascript-tests.json --workspace /path/to/js-project` | inspect, no network, no writes | [discover-javascript-tests.json](../examples/recipes/discover-javascript-tests.json) |
| Which local log files exist? | `term-mcp recipe run examples/recipes/analyze-logs.json --workspace .` | inspect, no network, no writes | [analyze-logs.json](../examples/recipes/analyze-logs.json) |
| Do service-port declarations agree? | `term-mcp recipe run examples/recipes/verify-port-config.json --workspace .` | inspect, no network, no writes | [verify-port-config.json](../examples/recipes/verify-port-config.json) |
| Does the public catalog stay inside the read-only boundary? | `term-mcp recipe run examples/recipes/read-only-boundary.json --workspace .` | inspect, no network, no writes | [read-only-boundary.json](../examples/recipes/read-only-boundary.json) |

Recipes use system commands that are present on the tested macOS and Ubuntu CI hosts. Results depend on the target repository, and empty discovery output can be valid. The catalog does not install dependencies, run project code, contact a model, or diagnose the meaning of arbitrary log content.
