"""End-to-end tests of the MCP tool layer (without stdio transport)."""

from __future__ import annotations

import json

import pytest

from brazilian_soccer_mcp.server import create_app

EXPECTED_TOOLS = {
    "search_matches",
    "head_to_head",
    "team_statistics",
    "team_comparison",
    "team_overview",
    "league_standings",
    "competition_statistics",
    "biggest_wins",
    "search_players",
    "player_profile",
    "search_knowledge_graph",
    "graph_neighbors",
}


@pytest.fixture(scope="module")
def app(engine):
    return create_app(engine)


def call_tool(app, name: str, arguments: dict) -> dict:
    """Invoke a tool through the MCP server and decode its JSON body."""
    import asyncio

    result = asyncio.run(app.call_tool(name, arguments))
    assert not result.is_error, result
    text = result.content[0].text
    return json.loads(text)


def list_tools(app) -> list:
    """List tools through the MCP server (synchronous wrapper)."""
    import asyncio

    return asyncio.run(app.list_tools())


class TestToolContract:
    def test_tools_are_registered(self, app) -> None:
        tools = list_tools(app)
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS <= names
        for tool in tools:
            assert tool.description, tool.name
            assert tool.input_schema.get("type") == "object"

    def test_json_schemas_expose_parameters(self, app) -> None:
        tools = {t.name: t for t in list_tools(app)}
        props = tools["search_matches"].input_schema["properties"]
        for param in ("team", "opponent", "competition", "season", "date_from", "date_to"):
            assert param in props


class TestToolCalls:
    def test_search_matches(self, app) -> None:
        out = call_tool(app, "search_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 10})
        assert out["count"] > 0
        assert out["matches"][0]["fixture"]

    def test_head_to_head(self, app) -> None:
        out = call_tool(app, "head_to_head", {"team_a": "Palmeiras", "team_b": "Corinthians"})
        assert out["record"]["played"] > 0

    def test_team_statistics(self, app) -> None:
        out = call_tool(app, "team_statistics", {"team": "Santos", "season": 2019, "competition": "Brasileirão Série A"})
        assert out["statistics"]["played"] == 38

    def test_team_comparison(self, app) -> None:
        out = call_tool(app, "team_comparison", {"team_a": "Palmeiras", "team_b": "Santos"})
        assert {"team_a", "team_b", "head_to_head"} <= set(out)

    def test_team_overview(self, app) -> None:
        out = call_tool(app, "team_overview", {"team": "Grêmio"})
        assert out["competitions"]
        assert out["player_count"] >= 0

    def test_league_standings(self, app) -> None:
        out = call_tool(app, "league_standings", {"competition": "Brasileirão Série A", "season": 2019})
        assert out["standings"][0]["team"] == "Flamengo"
        assert out["standings"][0]["points"] == 90

    def test_competition_statistics(self, app) -> None:
        out = call_tool(app, "competition_statistics", {"competition": "Copa do Brasil"})
        assert out["statistics"]["matches"] > 1000

    def test_biggest_wins(self, app) -> None:
        out = call_tool(app, "biggest_wins", {"limit": 5})
        assert out["count"] == 5

    def test_search_players(self, app) -> None:
        out = call_tool(app, "search_players", {"nationality": "Brazil", "min_overall": 85, "limit": 5})
        assert 0 < out["count"] <= 5

    def test_player_profile(self, app) -> None:
        out = call_tool(app, "player_profile", {"player_name": "Neymar"})
        assert out["player"]["overall"] == 92

    def test_graph_tools(self, app) -> None:
        out = call_tool(app, "search_knowledge_graph", {"query": "Libertadores", "node_types": ["Competition"]})
        assert out["count"] >= 1
        out = call_tool(app, "graph_neighbors", {"node_name": "Copa Libertadores"})
        assert out["count"] > 0

    def test_unicode_survives_roundtrip(self, app) -> None:
        out = call_tool(app, "team_statistics", {"team": "São Paulo"})
        assert out["query"]["team"] == "São Paulo"


class TestErrorHandling:
    def test_unknown_team_is_graceful(self, app) -> None:
        out = call_tool(app, "team_statistics", {"team": "Clube Nenhum 123"})
        assert "no team" in out["summary"].lower()

    def test_unknown_season_is_graceful(self, app) -> None:
        out = call_tool(app, "league_standings", {"competition": "Brasileirão Série A", "season": 1990})
        assert out["count"] == 0
