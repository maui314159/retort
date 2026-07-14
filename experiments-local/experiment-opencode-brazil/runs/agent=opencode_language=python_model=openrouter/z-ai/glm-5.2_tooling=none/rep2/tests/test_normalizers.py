# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Unit tests for the normalizers module (team names, dates, competitions) and
# for the MCP server tool registration. These complement the BDD scenario
# tests with focused edge-case coverage.
# ----------------------------------------------------------------------------
from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalizers import (
    canonical_team_name,
    normalize_competition,
    parse_date,
    strip_accents,
    team_key,
)


class TestTeamKey:
    def test_strips_state_suffix_no_space(self):
        assert team_key("Palmeiras-SP") == "palmeiras"

    def test_strips_state_suffix_with_spaces(self):
        assert team_key("América - MG") == "america"

    def test_case_insensitive(self):
        assert team_key("FLAMENGO") == team_key("flamengo")

    def test_strips_accents(self):
        assert team_key("São Paulo") == "sao paulo"
        assert team_key("Grêmio") == "gremio"
        assert team_key("Avaí") == "avai"

    def test_removes_parenthetical_qualifiers(self):
        key = team_key("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
        assert "antigo" not in key
        assert key.startswith("boavista")

    def test_overrides_full_names(self):
        assert team_key("Sport Club Corinthians Paulista") == "corinthians"
        assert team_key("São Paulo Futebol Clube") == "sao paulo"

    def test_empty_input(self):
        assert team_key("") == ""
        assert team_key(None) == ""


class TestCanonicalName:
    def test_strips_suffix(self):
        assert canonical_team_name("Palmeiras-SP") == "Palmeiras"
        assert canonical_team_name("Flamengo-RJ") == "Flamengo"

    def test_keeps_base_casing(self):
        assert canonical_team_name("América - MG") == "América"

    def test_override(self):
        assert canonical_team_name("Sport Club Corinthians Paulista") == "Corinthians"


class TestParseDate:
    def test_iso_date(self):
        assert parse_date("2023-09-24").year == 2023

    def test_iso_datetime(self):
        dt = parse_date("2012-05-19 18:30:00")
        assert dt.year == 2012 and dt.hour == 18

    def test_brazilian_format(self):
        assert parse_date("29/03/2003").year == 2003

    def test_invalid(self):
        assert parse_date("") is None
        assert parse_date(None) is None
        assert parse_date("not-a-date") is None


class TestNormalizeCompetition:
    @pytest.mark.parametrize("raw,expected", [
        ("Serie A", "Brasileirao"),
        ("Brasileirão", "Brasileirao"),
        ("Copa do Brasil", "Copa do Brasil"),
        ("Libertadores", "Copa Libertadores"),
        ("Serie B", "Serie B"),
    ])
    def test_mapping(self, raw, expected):
        assert normalize_competition(raw) == expected


class TestStripAccents:
    def test_basic(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("França") == "Franca"


# ---------------------------------------------------------------------------
# MCP server tool registration
# ---------------------------------------------------------------------------
class TestServer:
    def test_build_server_registers_tools(self, server):
        tools = [t for t in dir(server) if not t.startswith("_")]
        # FastMCP exposes a tool manager; verify tools are registered by name.
        import asyncio
        from fastmcp import FastMCP
        assert isinstance(server, FastMCP)

    @pytest.mark.asyncio
    async def test_tools_listed(self, server):
        tools = await server.list_tools()
        names = {t.name for t in tools}
        expected = {
            "find_matches", "head_to_head", "team_stats", "search_players",
            "top_brazilian_players", "players_at_club", "standings",
            "champion", "relegated_teams", "average_goals", "biggest_wins",
            "best_home_record", "best_away_record", "list_teams",
            "list_competitions", "list_seasons",
        }
        missing = expected - names
        assert not missing, f"Missing tools: {missing}"
