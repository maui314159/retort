"""MCP server integration tests: tool listing and end-to-end tool calls.

Uses the in-memory transport from the mcp SDK so the full protocol layer
(initialize -> list_tools -> call_tool) is exercised without stdio.
"""

import json

import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from brasil_mcp.server import build_server

EXPECTED_TOOLS = {
    "find_team",
    "search_matches",
    "head_to_head",
    "team_stats",
    "team_season_history",
    "standings",
    "search_players",
    "team_players",
    "competition_info",
    "derbies",
    "biggest_wins",
    "goals_analysis",
    "best_records",
    "compare_teams",
}


def run_with_client(callback) -> None:
    """Run an MCP server and client over in-memory streams for one session."""

    async def main():
        server = build_server()
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            async with ClientSession(*client_streams) as session:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(
                        server._lowlevel_server.run,
                        server_streams[0],
                        server_streams[1],
                        server._lowlevel_server.create_initialization_options(),
                    )
                    await session.initialize()
                    await callback(session)
                    tg.cancel_scope.cancel()

    anyio.run(main)


def test_all_expected_tools_are_listed():
    async def callback(session: ClientSession):
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        assert EXPECTED_TOOLS <= names
        assert all(tool.description for tool in tools.tools)

    run_with_client(callback)


def test_search_matches_tool_call():
    async def callback(session: ClientSession):
        result = await session.call_tool(
            "search_matches",
            {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
        )
        payload = json.loads(result.content[0].text)
        assert payload["total"] >= 40
        assert payload["matches"][0]["date"]
        assert "Head-to-head in dataset" in payload["summary"]

    run_with_client(callback)


def test_standings_tool_call():
    async def callback(session: ClientSession):
        result = await session.call_tool("standings", {"season": 2019})
        payload = json.loads(result.content[0].text)
        assert payload["champion"]["team"] == "Flamengo"
        assert "Champion" in payload["summary"]

    run_with_client(callback)


def test_search_players_tool_call():
    async def callback(session: ClientSession):
        result = await session.call_tool(
            "search_players", {"nationality": "Brazil", "limit": 5}
        )
        payload = json.loads(result.content[0].text)
        assert payload["total"] == 827
        assert payload["players"][0]["name"] == "Neymar Jr"

    run_with_client(callback)


def test_team_players_tool_graceful_for_missing_squad():
    async def callback(session: ClientSession):
        result = await session.call_tool("team_players", {"team": "Flamengo"})
        payload = json.loads(result.content[0].text)
        assert payload["total"] == 0
        assert "No FIFA squad found" in payload["summary"]

    run_with_client(callback)


def test_tool_result_is_valid_json_everywhere():
    """Every tool must return JSON-serializable content for LLM clients."""

    calls = [
        ("find_team", {"name": "Grêmio"}),
        ("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"}),
        ("team_stats", {"team": "Flamengo", "season": 2019}),
        ("team_season_history", {"team": "Santos"}),
        ("standings", {"season": 2019}),
        ("derbies", {"season": 2023}),
        ("biggest_wins", {"limit": 3}),
        ("goals_analysis", {"competition": "Série A"}),
        ("best_records", {"venue": "away"}),
        ("compare_teams", {"team_a": "Grêmio", "team_b": "Internacional"}),
        ("competition_info", {}),
    ]

    async def callback(session: ClientSession):
        for tool, kwargs in calls:
            result = await session.call_tool(tool, kwargs)
            payload = json.loads(result.content[0].text)
            assert isinstance(payload, dict) and "summary" in payload, tool

    run_with_client(callback)
