# Findings: protocol era and lifecycle

- The current stable MCP revision is `2026-07-28`. It uses stateless, self-contained requests with protocol version and client capabilities on every request.
- Modern servers must implement `server/discover`. A client may call another method directly and recover from `UnsupportedProtocolVersionError` (`-32022`).
- `initialize`, `notifications/initialized`, and protocol-level sessions belong to the legacy `2025-11-25` era. The official compatibility model explicitly permits a dual-era server.
- Modern request metadata lives in `params._meta` under `io.modelcontextprotocol/protocolVersion`, `io.modelcontextprotocol/clientInfo`, and `io.modelcontextprotocol/clientCapabilities`.
- Term MCP DeepSeek should therefore advertise modern `2026-07-28` first while preserving a scoped `2025-11-25` handshake path.

Official sources:

- https://modelcontextprotocol.io/specification/2026-07-28
- https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2025-11-25/schema
