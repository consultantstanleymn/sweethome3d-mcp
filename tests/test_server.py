import asyncio
import os
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def test_server_lists_and_calls_ping_over_stdio() -> None:
    async def run_client() -> None:
        project_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        src_path = str(project_root / "src")
        env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else src_path + os.pathsep + env["PYTHONPATH"]
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sh3d_mcp"],
            cwd=project_root,
            env=env,
        )

        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                assert "ping" in tool_names

                call_result = await session.call_tool("ping")
                assert call_result.is_error is False
                assert call_result.structured_content == {"ok": True, "message": "pong"}

    asyncio.run(run_client())
