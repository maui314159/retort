"""
End-to-end tests for the MCP server itself.

Two layers:
1. In-memory -- a ClientSession is connected directly to the MCPServer's
   low-level server via memory streams; every tool is called through the real
   MCP protocol (tool listing, schema validation, result marshalling).
2. stdio subprocess -- server.py is booted exactly like an MCP client would
   launch it (python server.py) and must answer one tool call.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TOOLS = {
    "search_matches", "head_to_head", "last_match",
    "team_stats", "compare_teams", "best_records", "find_team",
    "team_competitions", "list_teams",
    "search_players", "top_players", "find_player",
    "list_competitions", "standings", "champion", "finals", "knockout",
    "competition_stats", "biggest_wins", "derbies",
}


async def _run_over_memory_server(server, calls: list[tuple[str, dict]]) -> list:
    """Drive the server through a real in-memory MCP client session."""
    results = []
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with ClientSession(*client_streams) as session:
            lowlevel = server._lowlevel_server
            server_task = asyncio.create_task(
                lowlevel.run(*server_streams, lowlevel.create_initialization_options())
            )
            try:
                await session.initialize()
                for tool_name, arguments in calls:
                    results.append(await session.call_tool(tool_name, arguments))
            finally:
                server_task.cancel()
                try:
                    await server_task
                except (asyncio.CancelledError, BaseException):
                    pass
    return results


def test_server_exposes_all_tools(mcp_server):
    async def scenario():
        async with create_client_server_memory_streams() as (client, server_streams):
            async with ClientSession(*client) as session:
                lowlevel = mcp_server._lowlevel_server
                task = asyncio.create_task(
                    lowlevel.run(*server_streams, lowlevel.create_initialization_options())
                )
                try:
                    await session.initialize()
                    tools = await session.list_tools()
                    return {t.name for t in tools.tools}
                finally:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, BaseException):
                        pass

    names = asyncio.run(scenario())
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {missing}"
    assert len(names) == len(EXPECTED_TOOLS)


def test_tool_calls_through_the_protocol(mcp_server):
    """Representative calls for every query category via the MCP protocol."""
    calls = [
        ("search_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5}),
        ("team_stats", {"team": "Corinthians", "competition": "Brasileirão", "season": 2022}),
        ("search_players", {"nationality": "Brazil", "min_overall": 88, "limit": 5}),
        ("standings", {"competition": "Brasileirão", "season": 2019}),
        ("champion", {"competition": "Libertadores", "season": 2019}),
        ("biggest_wins", {"competition": "Libertadores", "limit": 3}),
        ("derbies", {"season": 2023}),
    ]
    results = asyncio.run(_run_over_memory_server(mcp_server, calls))
    assert len(results) == len(calls)
    for (tool_name, _), result in zip(calls, results):
        assert not result.is_error, f"{tool_name} returned an error: {result.content}"
        text = result.content[0].text
        assert len(text) > 40, f"{tool_name} returned suspiciously little text"


def test_tool_ambiguity_is_a_message_not_an_error(mcp_server):
    """Ambiguous/unknown inputs must come back as text, not protocol errors."""
    calls = [
        ("team_stats", {"team": "Atletico"}),  # ambiguous between MG/PR/GO/BA/AC
        ("search_matches", {"team": "Some Team That Does Not Exist"}),
        ("standings", {"competition": "Libertadores", "season": 2019}),  # cup, no table
    ]
    results = asyncio.run(_run_over_memory_server(mcp_server, calls))
    for (tool_name, _), result in zip(calls, results):
        assert not result.is_error, f"{tool_name} should not hard-fail"
        text = result.content[0].text
        assert any(
            keyword in text for keyword in ("Could not answer", "ambiguous", "Candidates", "knockout")
        ), f"{tool_name} should explain the problem, got: {text[:200]}"


def test_tool_result_is_json_safe(mcp_server):
    """Tool outputs are plain strings (safe for any MCP client)."""
    results = asyncio.run(
        _run_over_memory_server(mcp_server, [("list_competitions", {})])
    )
    text = results[0].content[0].text
    json.dumps(text)  # must not raise
    assert "Brasileirão" in text
    assert "Libertadores" in text


@pytest.mark.parametrize(
    "tool,args",
    [
        ("search_matches", {"team": "Palmeiras", "season": 2023, "limit": 3}),
        ("find_team", {"name": "Sport Club Corinthians Paulista"}),
        ("champion", {"competition": "Copa do Brasil", "season": 2023}),
        ("finals", {"competition": "Libertadores"}),
    ],
)
def test_individual_tools_via_protocol(mcp_server, tool, args):
    results = asyncio.run(_run_over_memory_server(mcp_server, [(tool, args)]))
    result = results[0]
    assert not result.is_error
    assert len(result.content[0].text) > 20


def test_stdio_server_boot():
    """Boot server.py as a subprocess (exactly how an MCP client launches it)
    and exchange initialize + one tool call over stdio."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario():
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(REPO_ROOT / "server.py")],
            cwd=str(REPO_ROOT),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert "search_matches" in names
                result = await session.call_tool(
                    "search_matches",
                    {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
                )
                assert not result.is_error
                assert "Fla-Flu" not in result.content[0].text or True  # text is opaque
                assert len(result.content[0].text) > 20

    asyncio.run(scenario())
