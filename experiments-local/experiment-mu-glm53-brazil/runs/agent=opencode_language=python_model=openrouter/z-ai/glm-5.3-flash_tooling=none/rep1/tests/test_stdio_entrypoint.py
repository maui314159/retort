"""End-to-end stdio test: launch `python -m brazilian_soccer_mcp` and drive
it with a real MCP client session (R1 entrypoint verification)."""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_server_roundtrip():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "brazilian_soccer_mcp"]
    )

    async def scenario():
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            result = await session.call_tool(
                "get_standings",
                {"competition": "brasileirao", "season": 2019},
            )
            payload = json.loads(result.content[0].text)
            return names, payload

    names, payload = asyncio.run(scenario())
    assert "search_matches" in names
    assert "head_to_head" in names
    assert payload["standings"][0]["team"] == "Flamengo"
