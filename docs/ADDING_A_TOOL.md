# Adding an MCP tool safely

A tool is a public capability and a new trust-boundary input. Add one only when a recipe cannot express the outcome through an existing narrow tool.

## Required path

1. Define required and optional arguments in `TOOL_ARGUMENTS`.
2. Add a JSON Schema with `additionalProperties: false` in `MCPServer.list_tools()`.
3. Choose accurate MCP annotations. A tool that can start a process is not read-only even if the intended command is.
4. Validate types and values before touching sessions, paths, files, processes, or the network.
5. Route terminal work through `ExecutionService`; never call `subprocess`, `os.system`, `shell=True`, or an interpreter from a tool handler.
6. Route paths through `CommandPolicy.resolve_cwd()` or `resolve_resource()` and keep them under `WORKSPACE_ROOT`.
7. Require session ownership for mutable state and clean it at close/expiry.
8. Return structured content and stable errors without tracebacks or private details.
9. Add modern and legacy protocol fixtures plus HTTP and STDIO tests.
10. Add adversarial tests for malformed arguments, extra fields, cross-session ids, path escape, symlink escape, output limits, timeout, cancellation, and model unavailability where relevant.

## Review checklist

- What new capability does this expose?
- Can the same result use an existing plan or resource operation?
- Which mode permits it: inspect, confirm, or trusted?
- What requires human approval?
- What is the maximum runtime, output, process count, and path scope?
- Which receipt fields prove the result?
- What remains unsupported?

A PR that adds direct arbitrary shell access, executes model text, weakens the default policy, or omits a regression test will not be accepted.
