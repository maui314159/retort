"""In-process MCP protocol tests for the server tool surface."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

import anyio
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from brazilian_soccer_mcp import server as srv
from brazilian_soccer_mcp.service import SoccerDataService


def _client_run(service: SoccerDataService, script) -> dict:
    """Drive the MCP server in-process and return collected results."""
    original = srv.get_service
    srv.get_service = lambda: service
    results: dict = {}

    async def runner():
        lowlevel = srv.mcp._lowlevel_server
        async with create_client_server_memory_streams() as (
            client_streams, server_streams,
        ):
            server_task = asyncio.create_task(
                lowlevel.run(
                    server_streams[0], server_streams[1],
                    lowlevel.create_initialization_options(),
                    raise_exceptions=True,
                )
            )
            try:
                async with ClientSession(*client_streams) as session:
                    await session.initialize()
                    await script(session, results)
            finally:
                server_task.cancel()
                with suppress(asyncio.CancelledError):
                    await server_task

    try:
        anyio.run(runner)
    finally:
        srv.get_service = original
    return results


def _call_json(session, tool: str, arguments: dict) -> dict:
    async def invoke():
        response = await session.call_tool(tool, arguments)
        assert not response.is_error, response.content
        payload = json.loads(response.content[0].text)
        assert isinstance(payload, dict)
        return payload
    return invoke()


def test_server_exposes_all_tools(service: SoccerDataService):
    async def script(session, results):
        response = await session.list_tools()
        results["tools"] = sorted(tool.name for tool in response.tools)

    results = _client_run(service, script)
    assert results["tools"] == sorted(srv.TOOL_NAMES)
    assert len(results["tools"]) == 15


def test_resolve_team_over_mcp(service: SoccerDataService):
    async def script(session, results):
        results["palmeiras"] = await _call_json(
            session, "resolve_team", {"name": "Palmeiras-SP"},
        )

    results = _client_run(service, script)
    assert results["palmeiras"]["found"] is True
    assert results["palmeiras"]["display"] == "Palmeiras"


def test_standings_over_mcp(service: SoccerDataService):
    async def script(session, results):
        results["standings"] = await _call_json(
            session, "standings",
            {"competition": "Brasileirão Série A", "season": 2019},
        )

    results = _client_run(service, script)
    standings = results["standings"]
    assert standings["champion"] == "Flamengo"
    assert standings["table"][0]["points"] == 90


def test_search_matches_over_mcp(service: SoccerDataService):
    async def script(session, results):
        results["h2h"] = await _call_json(
            session, "search_matches",
            {"team": "Flamengo", "opponent": "Fluminense", "limit": 5},
        )

    results = _client_run(service, script)
    payload = results["h2h"]
    assert payload["total"] >= 40
    assert len(payload["matches"]) == 5
    match = payload["matches"][0]
    for field in ("date", "home", "away", "home_goals", "away_goals",
                  "competition"):
        assert field in match


def test_player_tools_over_mcp(service: SoccerDataService):
    async def script(session, results):
        results["top"] = await _call_json(
            session, "top_players", {"nationality": "Brazil", "n": 3},
        )
        results["club"] = await _call_json(
            session, "search_players", {"club": "Santos", "limit": 3},
        )

    results = _client_run(service, script)
    assert results["top"]["players"][0]["name"] == "Neymar Jr"
    assert results["club"]["total"] > 0
    for player in results["club"]["players"]:
        assert player["club_key"] == "santos-sp"


def test_error_results_are_structured(service: SoccerDataService):
    async def script(session, results):
        results["unknown"] = await _call_json(
            session, "search_matches", {"team": "Some Unknown FC"},
        )

    results = _client_run(service, script)
    assert "error" in results["unknown"]
