# Findings: transports, tools, and conformance

- STDIO is newline-delimited UTF-8 JSON-RPC. Stdout may contain only protocol messages; diagnostics belong on stderr; EOF is graceful shutdown.
- Modern Streamable HTTP uses one POST per message at one MCP endpoint. Requests require `Accept: application/json, text/event-stream`, `MCP-Protocol-Version`, `Mcp-Method`, and `Mcp-Name` for named operations. Mirrored header/body mismatches use `-32020`.
- Modern Streamable HTTP removed protocol sessions and the standalone GET event stream. Legacy Streamable HTTP may mint `Mcp-Session-Id` during initialize and requires it on subsequent requests.
- Tool catalogs should be deterministic and may return cache hints. Tool execution failures belong in `CallToolResult` with `isError: true`; malformed protocol calls and unknown tools use JSON-RPC errors.
- Structured output should be returned both in `structuredContent` and as a serialized text content block for compatibility.
- The official Python SDK 2.1.1 can act as an executable interop oracle for modern and legacy clients. MCP Inspector provides a second independent CLI client.

Official sources:

- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://github.com/modelcontextprotocol/python-sdk
- https://github.com/modelcontextprotocol/inspector
