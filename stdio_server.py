#!/usr/bin/env python3
"""
MCP Server with STDIO Transport
This script runs the MCP server using standard input/output for communication,
which is useful for command-line integration and local clients.
"""

import sys
import json
import asyncio
import logging
from tools.json_rpc import JSONRPCServer, JSONRPCError

# Import our MCP methods
from server import (
    mcp_list_tools, mcp_call_tool, mcp_list_prompts, mcp_get_prompt,
    mcp_list_resources, mcp_read_resource, mcp_list_roots
)

def setup_stdio_logging():
    """Setup logging for STDIO mode"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr  # Log to stderr so stdout is clean for MCP messages
    )
    return logging.getLogger("mcp_stdio")

def main():
    """Main STDIO server loop"""
    logger = setup_stdio_logging()
    logger.info("Starting MCP server with STDIO transport")

    # Initialize JSON-RPC server
    jsonrpc_server = JSONRPCServer()

    # Register MCP methods
    jsonrpc_server.register_method("tools/list", mcp_list_tools)
    jsonrpc_server.register_method("tools/call", mcp_call_tool)
    jsonrpc_server.register_method("prompts/list", mcp_list_prompts)
    jsonrpc_server.register_method("prompts/get", mcp_get_prompt)
    jsonrpc_server.register_method("resources/list", mcp_list_resources)
    jsonrpc_server.register_method("resources/read", mcp_read_resource)
    jsonrpc_server.register_method("roots/list", mcp_list_roots)

    logger.info("MCP methods registered successfully")

    try:
        while True:
            # Read a line from stdin
            line = sys.stdin.readline()
            if not line:
                # EOF reached
                break

            line = line.strip()
            if not line:
                continue

            logger.info(f"Received request: {line[:100]}...")

            try:
                # Parse the JSON-RPC request
                request = json.loads(line)

                # Handle the request
                response = jsonrpc_server.handle_request()

                # Send the response to stdout
                response_json = json.dumps(response, separators=(',', ':'))
                print(response_json, flush=True)
                logger.info("Response sent")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()