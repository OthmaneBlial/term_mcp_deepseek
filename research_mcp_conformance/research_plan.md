# MCP conformance research plan

## Main question

Which current official Model Context Protocol contract should Term MCP DeepSeek target, and what exact lifecycle, capability, transport, tool-result, and error behavior must its HTTP and STDIO implementations satisfy?

## Subtopics

1. **Protocol version and lifecycle** — identify the current stable specification version, initialize negotiation rules, required notifications, advertised server capabilities, and pagination shapes.
2. **Transport and result semantics** — identify STDIO framing, Streamable HTTP requirements, session/version headers, structured tool content, protocol errors, and available official conformance/client tooling.

## Synthesis

Translate the official requirements into a pinned compatibility document, protocol state machine, transport implementation, and executable interop tests. Keep compatibility routes separate and document any intentional unsupported capability.
