# Safe recipe examples

Every recipe in `recipes/` is a small, inspect-only workflow. The JSON Schema and semantic validator require:

- an explicit intent and prerequisites;
- `inspect` mode, no network, and no writes;
- low-risk commands accepted by the same policy used in production;
- bounded runtime and output;
- an expected result and anonymized receipt preview.

Validate every example:

```bash
term-mcp recipe validate examples/recipes/*.json --workspace .
```

Run one against a repository:

```bash
term-mcp recipe run examples/recipes/inspect-repository.json --workspace .
```

The runner uses the normal plan → policy → execute → signed receipt engine. It does not invoke a shell and it stops on the first unexpected status.

To contribute, copy [recipe-template.json](recipe-template.json), keep the new file in `examples/recipes/`, add a focused test when behavior changes, and run `./local_ci.sh`. CI validates and executes every recipe.

| Recipe | Concrete question |
| --- | --- |
| `inspect-repository` | What state and tracked surface does this repository have? |
| `diagnose-tests` | Where is the test configuration and what test files exist? |
| `analyze-logs` | Which local log files are available for a later bounded review? |
| `verify-port-config` | Do environment and container files agree on the service port? |
| `read-only-boundary` | Can the engine produce receipts without write or network permission? |
