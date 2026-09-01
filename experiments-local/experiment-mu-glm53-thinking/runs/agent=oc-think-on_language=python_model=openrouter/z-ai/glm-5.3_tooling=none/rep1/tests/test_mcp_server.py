"""Feature: MCP Server Protocol

BDD scenarios exercising the server over the real stdio transport, exactly
as an MCP client (Claude Desktop, opencode, ...) would: initialize the
session, list tools, call them and read the JSON results.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = REPO_ROOT / "server.py"

EXPECTED_TOOLS = {
    "list_competitions",
    "resolve_team",
    "search_matches",
    "head_to_head",
    "get_team_stats",
    "get_club_overview",
    "get_standings",
    "get_relegation",
    "find_finals",
    "search_players",
    "get_competition_stats",
    "get_biggest_wins",
    "get_derby_matches",
    "search_match_stats",
    "best_home_records",
}


class SharedMCPServer:
    """One MCP server subprocess on a background event loop for the session."""

    def __init__(self, script: Path) -> None:
        self._params = StdioServerParameters(
            command=sys.executable, args=[str(script)], cwd=str(REPO_ROOT)
        )
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._failure: BaseException | None = None
        self._client: Client | None = None
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=120):
            raise RuntimeError("MCP server did not become ready in time")
        if self._failure is not None:
            raise self._failure

    def _serve(self) -> None:
        asyncio.set_event_loop(self._loop)

        async def main() -> None:
            async with Client(self._params) as client:
                self._client = client
                self._ready.set()
                await asyncio.Future()

        try:
            self._loop.run_until_complete(main())
        except BaseException as exc:  # noqa: BLE001 - record any startup failure
            if not self._ready.is_set():
                self._failure = exc
                self._ready.set()

    def _run(self, coro):
        assert self._client is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=120)

    def list_tools(self):
        return self._run(self._client.list_tools())

    def call(self, tool: str, arguments: dict) -> dict:
        """Call a tool and parse its JSON text payload."""
        result = self._run(self._client.call_tool(tool, arguments))
        assert result.is_error is False, f"tool {tool} failed"
        payload = json.loads(result.content[0].text)
        assert isinstance(payload, dict)
        return payload


@pytest.fixture(scope="module")
def server() -> SharedMCPServer:
    # Given the MCP server is launched over stdio
    server = SharedMCPServer(SERVER_SCRIPT)
    # And its data is warm (first call triggers the lazy dataset load)
    server.call("list_competitions", {})
    return server


class TestMcpSession:
    """Feature: MCP Server - Scenario: initialize and list tools."""

    def test_session_initializes_and_lists_all_tools(self, server):
        # Given an initialized stdio session
        # When the client lists tools
        tools = server.list_tools()
        # Then every documented tool is exposed with a schema and description
        names = {tool.name for tool in tools.tools}
        assert names == EXPECTED_TOOLS
        for tool in tools.tools:
            assert tool.description, f"tool {tool.name} lacks a description"
            assert tool.input_schema, f"tool {tool.name} lacks an input schema"


class TestMcpToolCalls:
    """Feature: MCP Server - Scenario: tool calls return structured JSON."""

    def test_get_standings_answers_who_won_2019(self, server):
        # Given the connected server
        # When I ask who won the 2019 Brasileirão
        result = server.call(
            "get_standings", {"competition": "Brasileirão Série A", "season": 2019}
        )
        # Then the champion and table come back as JSON
        assert result["champion"] == "Flamengo"
        assert result["table"][0]["points"] == 90

    def test_search_matches_head_to_head(self, server):
        # When I search Flamengo vs Fluminense matches
        result = server.call(
            "search_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5}
        )
        # Then 44 matches are found and the payload is limited
        assert result["total_matches"] == 44
        assert result["returned"] == 5
        assert result["truncated"] is True

    def test_search_players_top_brazilians(self, server):
        # When I ask for the top Brazilian players
        result = server.call(
            "search_players", {"nationality": "Brazil", "min_overall": 88, "limit": 3}
        )
        # Then Neymar Jr leads the list
        assert result["players"][0]["name"] == "Neymar Jr"
        assert result["players"][0]["overall"] == 92

    def test_resolve_team_handles_name_variations(self, server):
        # When I resolve a state-suffixed name
        result = server.call("resolve_team", {"name": "Corinthians-SP"})
        # Then the canonical club and variants are returned
        assert result["key"] == "corinthians"
        variants = {v["name"] for v in result["variants"]}
        assert "Corinthians" in variants

    def test_get_team_stats_home_record(self, server):
        # When I ask for Corinthians' 2019 home record
        result = server.call(
            "get_team_stats",
            {"team": "Corinthians", "season": 2019, "venue": "home", "competition": "Série A"},
        )
        # Then the record is returned
        assert result["record"]["matches"] == 19
        assert result["record"]["wins"] == 10

    def test_find_finals_libertadores(self, server):
        # When I ask for the 2018 Libertadores final
        result = server.call("find_finals", {"competition": "Libertadores", "season": 2018})
        # Then River Plate is returned as the winner
        assert result["finals"][0]["winner_on_aggregate"] == "River Plate"

    def test_error_responses_are_structured_not_exceptions(self, server):
        # Given a misspelled team name
        # When I call the search tool
        result = server.call("search_matches", {"team": "Flamengoo"})
        # Then the tool returns a structured error with suggestions
        assert "error" in result
        assert "Flamengoo" in result["error"]
        assert "resolve_team" in result["error"]
