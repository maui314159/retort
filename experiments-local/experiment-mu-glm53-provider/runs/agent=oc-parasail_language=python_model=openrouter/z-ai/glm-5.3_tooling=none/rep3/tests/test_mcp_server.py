"""BDD steps for mcp_server.feature plus a real stdio end-to-end test.

The stdio test launches ``python server.py`` as a subprocess, connects a
ClientSession over the MCP stdio transport, and calls a tool - proving
the server is usable from a real MCP client.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import parsers, scenarios, then, when

from conftest import run_async

scenarios("features/mcp_server.feature")

EXPECTED_TOOLS = [
    "search_matches",
    "search_players",
    "standings",
    "head_to_head",
    "champion",
]


@when("I list the available tools")
def list_tools(server, ctx):
    tools = run_async(server.list_tools())
    ctx["tools"] = tools


@then("at least 15 tools should be available")
def fifteen_tools(ctx):
    assert len(ctx["tools"]) >= 15


@then(parsers.parse('the tool list should include "{first}", "{second}", "{third}", "{fourth}" and "{fifth}"'))
def tools_include(ctx, first, second, third, fourth, fifth):
    names = {t.name for t in ctx["tools"]}
    for expected in EXPECTED_TOOLS:
        assert expected in names, f"missing tool {expected}"


@then("the server should expose the datasets resource")
def has_resource(server):
    resources = run_async(server.list_resources())
    uris = {str(r.uri) for r in resources}
    assert any("datasets" in uri for uri in uris), uris


# ---------------------------------------------------------------------------
# Real stdio end-to-end test (subprocess + ClientSession)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stdio_end_to_end(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_py = Path(__file__).resolve().parent.parent / "server.py"
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_py)],
        cwd=str(server_py.parent),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.server_info.name == "brazilian-soccer"

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert "search_matches" in names
            assert "standings" in names

            result = await session.call_tool(
                "champion",
                {"competition": "Brasileirão", "season": 2019},
            )
            text = "".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            assert "Flamengo" in text

            result = await session.call_tool(
                "search_players",
                {"nationality": "Brazil", "limit": 3},
            )
            text = "".join(
                block.text for block in result.content if hasattr(block, "text")
            )
            assert "Neymar Jr" in text
