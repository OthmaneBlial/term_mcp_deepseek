import asyncio
import os
import sys
import threading
from pathlib import Path

import httpx2
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from werkzeug.serving import make_server

from term_mcp_deepseek.app import create_app
from term_mcp_deepseek.config import Settings

TOKEN = "official-client-token-that-is-longer-than-thirty-two"


async def assert_client_flow(client):
    tools = await client.list_tools()
    plan = await client.call_tool("terminal_plan", {"command": "pwd"})

    assert {tool.name for tool in tools.tools} >= {"terminal_plan", "terminal_execute"}
    assert plan.is_error is False
    assert plan.structured_content["status"] == "planned"
    assert plan.structured_content["policy"]["allowed"] is True


def test_official_client_interoperates_over_stdio_in_both_eras(tmp_path):
    async def exercise():
        environment = {
            "PATH": os.environ["PATH"],
            "PYTHONPATH": str(Path.cwd()),
            "WORKSPACE_ROOT": str(tmp_path),
        }
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "term_mcp_deepseek", "stdio"],
            cwd=Path.cwd(),
            env=environment,
        )
        for mode in ("auto", "legacy"):
            async with Client(parameters, mode=mode) as client:
                await assert_client_flow(client)
                expected = "2026-07-28" if mode == "auto" else "2025-11-25"
                assert client.protocol_version == expected

    asyncio.run(exercise())


def test_official_client_interoperates_over_http_in_both_eras(tmp_path):
    app = create_app(
        Settings(
            workspace_root=str(tmp_path),
            auth_token=TOKEN,
            allowed_origins=("http://127.0.0.1",),
        )
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def exercise():
        async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"}) as http_client:
            for mode in ("auto", "legacy"):
                transport = streamable_http_client(
                    f"http://127.0.0.1:{server.server_port}/mcp",
                    http_client=http_client,
                )
                async with Client(transport, mode=mode) as client:
                    await assert_client_flow(client)
                    expected = "2026-07-28" if mode == "auto" else "2025-11-25"
                    assert client.protocol_version == expected

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        thread.join(timeout=2)
        app.close_term_mcp()
