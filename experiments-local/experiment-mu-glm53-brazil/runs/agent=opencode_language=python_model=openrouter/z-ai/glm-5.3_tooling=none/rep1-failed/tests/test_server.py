"""BDD tests for the MCP server surface (protocol level).

Feature: MCP server
  Scenario: An MCP client connects and uses the tools
    Given the server is built
    When the client lists tools and calls them
    Then all 14 tools are advertised and return text results
"""

from __future__ import annotations

import pytest

from server import build_server

EXPECTED_TOOLS = {
    "list_competitions",
    "list_teams",
    "search_matches",
    "head_to_head",
    "team_stats",
    "team_profile",
    "search_players",
    "top_players",
    "player_profile",
    "standings",
    "finals",
    "biggest_wins",
    "stats",
    "derbies",
}


@pytest.fixture(scope="module")
def server():
    return build_server()


class TestToolRegistration:
    """Scenario: Tool discovery"""

    @pytest.mark.anyio
    async def test_all_tools_advertised(self, server):
        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS <= names
        assert len(names) == len(EXPECTED_TOOLS)

    @pytest.mark.anyio
    async def test_tools_have_descriptions(self, server):
        tools = await server.list_tools()
        for tool in tools:
            assert tool.description and len(tool.description) > 20, tool.name

    @pytest.mark.anyio
    async def test_tool_input_schemas(self, server):
        tools = {t.name: t for t in await server.list_tools()}
        match_schema = tools["search_matches"].input_schema
        assert match_schema["type"] == "object"
        assert "team" in match_schema["properties"]
        # parameters with defaults should not be required
        assert match_schema.get("required", []) == []


class TestToolCalls:
    """Scenario: Calling tools directly on the server object"""

    @pytest.mark.anyio
    async def test_call_standings(self, server):
        result = await server.call_tool("standings", {"competition": "brasileirao", "season": 2019})
        text = result.content[0].text
        assert "Flamengo" in text and "90 pts" in text

    @pytest.mark.anyio
    async def test_call_search_matches(self, server):
        result = await server.call_tool(
            "search_matches",
            {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
        )
        text = result.content[0].text
        assert "Head-to-head" in text

    @pytest.mark.anyio
    async def test_call_top_players(self, server):
        result = await server.call_tool("top_players", {"nationality": "Brazil", "limit": 3})
        assert "Neymar Jr" in result.content[0].text

    @pytest.mark.anyio
    async def test_optional_parameters_defaulted(self, server):
        """All tool parameters are optional where the spec allows broad queries."""
        result = await server.call_tool("stats", {})
        assert "Average goals per match" in result.content[0].text

    @pytest.mark.anyio
    async def test_unknown_tool_raises(self, server):
        from mcp.shared.exceptions import MCPError

        with pytest.raises(MCPError):
            await server.call_tool("nonexistent_tool", {})

    @pytest.mark.anyio
    async def test_invalid_arguments_raise(self, server):
        from mcp.shared.exceptions import MCPError

        with pytest.raises(MCPError):
            # standings requires a competition string; pass a wrong type
            await server.call_tool("standings", {"competition": 12345})


class TestInMemoryEndToEnd:
    """Scenario: A real client session over the in-memory transport"""

    @pytest.mark.anyio
    async def test_client_session_round_trip(self):
        from mcp.client._memory import InMemoryTransport
        from mcp.client.session import ClientSession

        server = build_server()
        async with InMemoryTransport(server) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                init = await session.initialize()
                assert init.server_info.name == "brazilian-soccer"

                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == EXPECTED_TOOLS

                result = await session.call_tool(
                    "search_players", {"nationality": "Brazil", "limit": 3}
                )
                assert not result.is_error
                assert "Neymar Jr" in result.content[0].text

    @pytest.mark.anyio
    async def test_client_multiple_tool_calls(self):
        from mcp.client._memory import InMemoryTransport
        from mcp.client.session import ClientSession

        server = build_server()
        async with InMemoryTransport(server) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                for tool, args, expect in [
                    ("list_competitions", {}, "Brasileirão Série A"),
                    ("standings", {"competition": "serie a", "season": 2019}, "Flamengo"),
                    ("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"}, "Head-to-head"),
                    ("derbies", {"season": 2019}, "Fla-Flu"),
                ]:
                    result = await session.call_tool(tool, args)
                    assert not result.is_error
                    assert expect in result.content[0].text, tool


class TestPerformance:
    """Spec: simple lookups < 2s, aggregate queries < 5s (data preloaded)."""

    @pytest.mark.anyio
    async def test_simple_lookup_under_2s(self, server):
        import time

        start = time.perf_counter()
        await server.call_tool("search_matches", {"team": "Flamengo", "limit": 5})
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    @pytest.mark.anyio
    async def test_aggregate_under_5s(self, server):
        import time

        start = time.perf_counter()
        await server.call_tool("stats", {})
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0
