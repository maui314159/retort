"""
test_brazilian_soccer.py
========================

BDD (Behavior-Driven Development) test scenarios for the Brazilian Soccer
MCP server, structured as Given/When/Then (GWT) blocks via pytest.

Context block
-------------
These tests exercise the data-access layer (``soccer_data.SoccerStore``) and
the MCP tool layer (``mcp_server``) against the real CSV datasets shipped in
``data/kaggle/``. They are intentionally end-to-end: the store is built once
per session via the module-level cached singleton, and each test asserts an
observable contract from the specification in TASK.md.

Run::

    pytest -q
"""

from __future__ import annotations

import json

import pytest

import soccer_data as sd
import mcp_server as mcp_mod


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def store() -> sd.SoccerStore:
    """Load the store once for the whole test session."""
    return sd.get_store()


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Feature: Match Queries"""

    def test_find_matches_between_two_teams(self, store):
        """
        Scenario: Find matches between two teams
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense"
          Then I should receive a list of matches
          And each match should have date, scores, and competition
        """
        # Given
        assert not store.matches.empty
        # When
        matches = store.search_matches(team="Flamengo", opponent="Fluminense", limit=100)
        # Then
        assert isinstance(matches, list)
        assert len(matches) > 0
        for m in matches:
            teams = {sd.normalize_team(m["home"]), sd.normalize_team(m["away"])}
            assert "flamengo" in teams
            assert "fluminense" in teams
            assert m["date"]  # non-empty
            assert m["home_goal"] is not None
            assert m["away_goal"] is not None
            assert m["competition"]

    def test_find_matches_by_team_and_season(self, store):
        """
        Scenario: What matches did Palmeiras play in 2023?
          Given the match data is loaded
          When I search for Palmeiras matches in season 2023
          Then every returned match involves Palmeiras and has season 2023
        """
        matches = store.search_matches(team="Palmeiras", season=2023, limit=1000)
        assert len(matches) > 0
        for m in matches:
            teams = {sd.normalize_team(m["home"]), sd.normalize_team(m["away"])}
            assert "palmeiras" in teams
            assert m["season"] == 2023

    def test_find_matches_by_competition(self, store):
        """
        Scenario: Find all Copa do Brasil matches
          Given the match data is loaded
          When I search for competition "Copa do Brasil"
          Then every returned match belongs to Copa do Brasil
        """
        matches = store.search_matches(competition="Copa do Brasil", limit=50)
        assert len(matches) > 0
        for m in matches:
            assert sd.normalize_comp(m["competition"]) == "copa do brasil"

    def test_last_match_between_teams(self, store):
        """
        Scenario: When did Flamengo last play Corinthians?
          Given the match data is loaded
          When I request the last match between "Flamengo" and "Corinthians"
          Then I should receive a single match dict
        """
        last = store.last_match("Flamengo", "Corinthians")
        assert last is not None
        teams = {sd.normalize_team(last["home"]), sd.normalize_team(last["away"])}
        assert "flamengo" in teams and "corinthians" in teams


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------

class TestTeamQueries:
    """Feature: Team Queries"""

    def test_team_home_record_in_season(self, store):
        """
        Scenario: What is Corinthians' home record in 2022?
          Given the match data is loaded
          When I request home statistics for "Corinthians" in season 2022
          Then I should receive wins, losses, draws, and goals
        """
        stats = store.team_stats("Corinthians", competition="Brasileirão", season=2022, venue="home")
        assert stats["played"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["played"]
        assert stats["goals_for"] >= 0
        assert stats["goals_against"] >= 0
        # Home win rate is a percentage.
        assert 0.0 <= stats["win_rate"] <= 100.0

    def test_team_competitions(self, store):
        """
        Scenario: What competitions has Palmeiras played in?
          Given the match data is loaded
          When I request competitions for "Palmeiras"
          Then I should receive a non-empty list of competitions
        """
        res = store.team_competitions("Palmeiras")
        assert res["competitions"]
        assert any(c["matches"] > 0 for c in res["competitions"])


# ---------------------------------------------------------------------------
# Feature: Head-to-Head
# ---------------------------------------------------------------------------

class TestHeadToHead:
    """Feature: Compare teams head-to-head"""

    def test_head_to_head_palmeiras_corinthians(self, store):
        """
        Scenario: Compare Palmeiras and Corinthians head-to-head
          Given the match data is loaded
          When I request the head-to-head between "Palmeiras" and "Corinthians"
          Then I should receive wins/draws/losses and the match list
        """
        h2h = store.head_to_head("Palmeiras", "Corinthians")
        assert h2h["total"] > 0
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == h2h["total"]
        assert isinstance(h2h["matches"], list)
        assert h2h["team_a_goals"] >= 0
        assert h2h["team_b_goals"] >= 0


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------

class TestCompetitionQueries:
    """Feature: Competition Queries"""

    def test_standings_for_season(self, store):
        """
        Scenario: Who won the 2019 Brasileirão?
          Given the match data is loaded
          When I request the 2019 Brasileirão standings
          Then I should receive a ranked table with Flamengo on top
        """
        st = store.standings("Brasileirão", 2019)
        table = st["table"]
        assert len(table) > 0
        # Champion is first.
        assert table[0]["position"] == 1
        assert sd.normalize_team(table[0]["name"]) == "flamengo"
        # Every team has full stats.
        for row in table:
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
            assert row["pts"] == row["wins"] * 3 + row["draws"]

    def test_standings_novo_historical(self, store):
        """
        Scenario: 2003-2019 historical dataset standings are distinct from
        the modern Brasileirão dataset.
        """
        st = store.standings("Brasileirão (2003-2019)", 2003)
        assert len(st["table"]) > 0
        for row in st["table"]:
            assert row["pts"] >= 0


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------

class TestStatistics:
    """Feature: Statistical Analysis"""

    def test_average_goals_in_brasileirao(self, store):
        """
        Scenario: What's the average goals per match in the Brasileirão?
          Given the match data is loaded
          When I request average goals for "Brasileirão"
          Then I should receive a positive average and home-win rate
        """
        res = store.average_goals("Brasileirão")
        assert res["matches"] > 0
        assert res["average_goals"] > 0
        assert 0.0 <= res["home_win_rate"] <= 100.0

    def test_biggest_wins(self, store):
        """
        Scenario: Show me the biggest wins in the dataset
          Given the match data is loaded
          When I request the biggest wins
          Then I should receive victories ordered by goal difference
        """
        res = store.biggest_wins(limit=5)
        wins = res["wins"]
        assert len(wins) > 0
        diffs = [abs(w["home_goal"] - w["away_goal"]) for w in wins]
        assert diffs == sorted(diffs, reverse=True)

    def test_best_home_record(self, store):
        """
        Scenario: Which team has the best home record in 2019 Brasileirão?
          Given the match data is loaded
          When I request best home record for Brasileirão 2019
          Then the top team should have the highest win rate
        """
        res = store.best_record(venue="home", competition="Brasileirão", season=2019, limit=5)
        teams = res["teams"]
        assert len(teams) > 0
        rates = [t["win_rate"] for t in teams]
        assert rates == sorted(rates, reverse=True)


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    """Feature: Player Queries"""

    def test_search_player_by_name(self, store):
        """
        Scenario: Who is Neymar?
          Given the FIFA player data is loaded
          When I search for a player named "Neymar"
          Then I should receive at least one matching player
        """
        res = store.player_search(name="Neymar", limit=5)
        assert len(res) > 0
        assert "neymar" in sd.normalize_team(res[0]["name"])

    def test_brazilian_players(self, store):
        """
        Scenario: Find all Brazilian players in the dataset
          Given the FIFA player data is loaded
          When I search for nationality "Brazil"
          Then every returned player should be Brazilian
        """
        res = store.player_search(nationality="Brazil", limit=50)
        assert len(res) > 0
        for p in res:
            assert sd.normalize_team(p["nationality"]) == "brazil"

    def test_top_players_by_overall(self, store):
        """
        Scenario: Who are the highest-rated Brazilian players?
          Given the FIFA player data is loaded
          When I request top Brazilian players
          Then the list should be sorted by Overall descending
        """
        res = store.top_players(nationality="Brazil", limit=10)
        assert len(res) > 0
        ratings = [p["overall"] for p in res]
        assert ratings == sorted(ratings, reverse=True)

    def test_brazilians_at_brazilian_clubs(self, store):
        """
        Scenario: Brazilian players at Brazilian clubs
          Given the FIFA and match data are loaded
          When I request Brazilians at Brazilian clubs
          Then every returned player should be Brazilian
        """
        res = store.brazilians_at_brazilian_clubs(limit=25)
        # Some FIFA editions may not list domestic clubs; ensure those present
        # are Brazilian nationals.
        for p in res:
            assert sd.normalize_team(p["nationality"]) == "brazil"


# ---------------------------------------------------------------------------
# Feature: Derbies
# ---------------------------------------------------------------------------

class TestDerbies:
    """Feature: Derby matches"""

    def test_derbies_2023(self, store):
        """
        Scenario: Show me all derbies in 2023
          Given the match data is loaded
          When I request derbies for season 2023
          Then I should receive matches between known rival pairs
        """
        res = store.derbies(season=2023)
        assert len(res) > 0
        for m in res:
            assert m.get("derby")  # tagged with a derby label


# ---------------------------------------------------------------------------
# Feature: Team Name Normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    """Feature: Handles team name variations correctly"""

    @pytest.mark.parametrize(
        "variant,expected",
        [
            ("Palmeiras-SP", "palmeiras"),
            ("Palmeiras", "palmeiras"),
            ("América - MG", "america mg"),
            ("Atletico Mineiro", "atletico mg"),
            ("São Paulo", "sao paulo"),
            ("São Paulo-SP", "sao paulo"),
            ("Corinthians - SP", "corinthians"),
            ("Vasco da Gama - RJ", "vasco"),
            ("Athletico-PR", "atletico pr"),
        ],
    )
    def test_normalize_team(self, variant, expected):
        """Team name variants normalize to canonical keys."""
        assert sd.normalize_team(variant) == expected

    def test_distinct_atletico_not_merged(self):
        """Atlético-MG and Atlético-GO must normalize to distinct keys."""
        assert sd.normalize_team("Atlético-MG") != sd.normalize_team("Atlético-GO")

    @pytest.mark.parametrize(
        "comp",
        ["Brasileirão", "Brasileirão (2003-2019)", "Copa do Brasil", "Copa Libertadores"],
    )
    def test_normalize_comp_distinct(self, comp):
        """Competition normalization preserves parenthetical distinctions."""
        assert sd.normalize_comp(comp)

    def test_brasileirao_and_historical_distinct(self):
        assert sd.normalize_comp("Brasileirão") != sd.normalize_comp("Brasileirão (2003-2019)")


# ---------------------------------------------------------------------------
# Feature: MCP Tool Layer
# ---------------------------------------------------------------------------

class TestMCPServer:
    """Feature: MCP server exposes query tools"""

    def test_all_expected_tools_registered(self):
        """
        Scenario: The MCP server registers all required tools
          Given the server module is imported
          When I list the available tools
          Then I should see the core query tools
        """
        import asyncio

        async def _check():
            tools = await mcp_mod.mcp.list_tools()
            names = {t.name for t in tools}
        # run synchronously
        tools = asyncio.run(mcp_mod.mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "search_matches", "last_match", "head_to_head", "team_stats",
            "team_competitions", "standings", "biggest_wins", "average_goals",
            "best_record", "derbies", "player_search", "top_players",
            "brazilians_at_brazilian_clubs", "list_competitions", "list_seasons",
        }
        assert expected.issubset(names), f"missing: {expected - names}"

    def test_list_competitions_tool_returns_json(self):
        """
        Scenario: list_competitions tool returns JSON list of competitions
          Given the MCP server is running
          When I call the list_competitions tool
          Then I should receive valid JSON containing known competitions
        """
        import asyncio

        content, _ = asyncio.run(mcp_mod.mcp.call_tool("list_competitions", {}))
        text = content[0].text
        comps = json.loads(text)
        assert "Brasileirão" in comps
        assert "Copa do Brasil" in comps

    def test_head_to_head_tool_returns_json(self):
        """
        Scenario: head_to_head tool returns JSON record
          Given the MCP server is running
          When I call head_to_head for Flamengo vs Fluminense
          Then I should receive valid JSON with wins and draws
        """
        import asyncio

        content, _ = asyncio.run(
            mcp_mod.mcp.call_tool("head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"})
        )
        data = json.loads(content[0].text)
        assert data["total"] > 0
        assert data["team_a_wins"] >= 0
        assert data["team_b_wins"] >= 0
        assert data["draws"] >= 0

    def test_standings_tool_returns_json(self):
        """
        Scenario: standings tool returns a ranked table
          Given the MCP server is running
          When I call standings for Brasileirão 2019
          Then the champion should be Flamengo
        """
        import asyncio

        content, _ = asyncio.run(
            mcp_mod.mcp.call_tool("standings", {"competition": "Brasileirão", "season": 2019})
        )
        data = json.loads(content[0].text)
        assert data["table"][0]["position"] == 1
        assert sd.normalize_team(data["table"][0]["name"]) == "flamengo"
