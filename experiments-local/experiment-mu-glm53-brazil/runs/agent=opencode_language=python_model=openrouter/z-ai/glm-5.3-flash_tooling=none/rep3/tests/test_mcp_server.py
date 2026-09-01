"""End-to-end test: the real MCP server over stdio, driven by an MCP client.

Each test spawns the server once (stdio) and drives it with the official
MCP client; the whole client lifecycle runs inside a single ``asyncio.run``
task because anyio cancel-scopes must be entered and exited in one task.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Awaitable, Callable


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "server.py")
REPO = os.path.dirname(SERVER)

EXPECTED_TOOLS = {
    "search_matches", "get_head_to_head", "get_team_stats", "get_team_history",
    "list_teams", "get_competitions", "get_standings", "compare_seasons",
    "search_players", "get_player", "search_players_at_club",
    "get_statistics", "get_derbies", "answer_question",
}


async def _with_session(do: Callable[[ClientSession], Awaitable]):
    params = StdioServerParameters(command=sys.executable, args=[SERVER], cwd=REPO)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await do(session)


def run_with_server(do):
    return asyncio.run(_with_session(do))


def call_tool(tool: str, args: dict) -> dict:
    async def _do(session: ClientSession):
        res = await session.call_tool(tool, args)
        return json.loads(res.content[0].text)
    return run_with_server(_do)


def test_server_lists_all_tools():
    async def _do(session: ClientSession):
        res = await session.list_tools()
        return {t.name for t in res.tools}
    assert EXPECTED_TOOLS <= run_with_server(_do)


def test_search_matches_tool():
    data = call_tool("search_matches",
                     {"team": "Flamengo", "season": 2023, "limit": 5})
    assert data["total"] > 0
    assert data["matches"][0]["season"] == 2023


def test_head_to_head_tool():
    data = call_tool("get_head_to_head",
                     {"team_a": "Flamengo", "team_b": "Fluminense"})
    assert data["derby"] == "Fla-Flu"
    assert data["total_matches"] > 30


def test_standings_tool():
    data = call_tool("get_standings",
                     {"competition": "Brasileirão Serie A", "season": 2019,
                      "top": 3})
    assert data["champion"] == "Flamengo-RJ"


def test_player_tool():
    data = call_tool("get_player", {"name": "Neymar Jr"})
    assert data["name"] == "Neymar Jr"
    assert data["overall"] == 92


def test_answer_question_tool():
    data = call_tool("answer_question",
                     {"question": "Who won the 2019 Brasileirão?"})
    assert data["result"]["champion"] == "Flamengo-RJ"


def test_error_is_structured_json():
    data = call_tool("get_team_stats", {"team": "Narnia United"})
    assert "error" in data


def test_status_resource():
    from mcp.types import AnyUrl

    async def _do(session: ClientSession):
        res = await session.read_resource(AnyUrl("soccer://status"))
        return json.loads(res.contents[0].text)
    data = run_with_server(_do)
    assert data["matches"] > 15000
    assert data["players"] == 18207
