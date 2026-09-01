"""BDD-style test scenarios for the Brazilian Soccer MCP Server.

Mirrors the Gherkin scenarios in TASK.md: match queries, team queries,
player queries, competition queries, and statistical analysis.
"""

import asyncio
import time

import pytest

from brazilian_soccer import SoccerData, SoccerQueries
from brazilian_soccer.loader import name_matches, normalize_name, parse_date


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return SoccerData()


@pytest.fixture(scope="session")
def q(data) -> SoccerQueries:
    return SoccerQueries(data)


# ---------------------------------------------------------------------------
# Feature: Data loading
# ---------------------------------------------------------------------------

class TestFeatureDataLoading:
    def test_all_six_csv_files_are_loaded(self, data):
        """Scenario: All 6 CSV files are loadable and queryable."""
        assert len(data.matches) >= 12000  # 4180 + 1337 + 1255 + 10296 + 6886
        assert len(data.players) == 18207

    def test_matches_have_required_fields(self, data):
        """Scenario: Each match has date, scores, and competition."""
        for m in data.matches[:500]:
            assert m.competition
            assert m.home and m.away


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestFeatureMatchQueries:
    def test_find_matches_between_two_teams(self, q):
        """Scenario: Find matches between two teams."""
        matches = q.find_matches(team="Flamengo", opponent="Fluminense")
        assert matches, "expected Flamengo vs Fluminense matches"
        for m in matches:
            assert name_matches("Flamengo", m.home) or name_matches("Flamengo", m.away)
            assert name_matches("Fluminense", m.home) or name_matches("Fluminense", m.away)
            assert m.home_goal is not None
            assert m.away_goal is not None
            assert m.date is not None
            assert m.competition

    def test_find_matches_by_team_and_season(self, q):
        """Scenario: What matches did Palmeiras play in 2023?"""
        matches = q.find_matches(team="Palmeiras", season=2023)
        assert matches
        for m in matches:
            assert name_matches("Palmeiras", m.home) or name_matches("Palmeiras", m.away)
            assert m.season == 2023

    def test_find_matches_by_competition(self, q):
        """Scenario: Find matches by competition (Copa do Brasil)."""
        matches = q.find_matches(competition="Copa do Brasil", season=2012, limit=50)
        assert matches
        for m in matches:
            assert "copa do brasil" in normalize_name(m.competition)

    def test_find_matches_by_date_range(self, q):
        matches = q.find_matches(date_from="2023-09-01", date_to="2023-09-30", limit=100)
        assert matches
        for m in matches:
            assert m.date.strftime("%Y-%m") == "2023-09"

    def test_last_match_between(self, q):
        m = q.last_match_between("Flamengo", "Corinthians")
        assert m is not None
        h2h = q.data.head_to_head("Flamengo", "Corinthians")
        assert m.date >= max(x.date for x in h2h if x.date)

    def test_formatted_output_includes_scores(self, q):
        text = q.format_match_list(q.find_matches(team="Flamengo", opponent="Fluminense", limit=3))
        assert "Flamengo" in text
        assert "(" in text  # competition in parentheses


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------

class TestFeatureTeamQueries:
    def test_team_statistics(self, q):
        """Scenario: Get team statistics for a season."""
        stats = q.team_stats("Palmeiras", season=2023, competition="Brasileirão")
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        assert stats["goals_for"] >= 0

    def test_home_record_2022(self, q):
        """Scenario: What is Corinthians' home record in 2022?"""
        stats = q.team_stats("Corinthians", season=2022, venue="home")
        assert stats["matches"] > 0
        assert 0 <= stats["win_rate"] <= 100

    def test_head_to_head_summary(self, q):
        """Scenario: Compare Palmeiras and Santos head-to-head."""
        s = q.head_to_head_summary("Palmeiras", "Santos")
        assert s["matches"] > 20
        assert (
            s["team_a_wins"] + s["team_b_wins"] + s["draws"] == s["matches"]
        )

    def test_team_competitions(self, q):
        summary = q.matches_per_team_summary("Palmeiras")
        assert summary["competitions"]

    def test_nonexistent_team_has_zero_matches(self, q):
        stats = q.team_stats("NoSuchTeam FC")
        assert stats["matches"] == 0


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestFeaturePlayerQueries:
    def test_search_player_by_name(self, q):
        players = q.search_players(name="Gabriel Jesus")
        assert players
        assert any("gabriel jesus" in p["_norm_name"] for p in players)

    def test_brazilian_players(self, q):
        players = q.search_players(nationality="Brazil", limit=50)
        assert len(players) == 50
        for p in players:
            assert p["Nationality"] == "Brazil"
        ratings = [p["Overall"] for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_players_at_club(self, q):
        players = q.search_players(club="Santos", limit=10)
        assert players
        for p in players:
            assert "santos" in p["_norm_club"]

    def test_forwards_from_santos(self, q):
        players = q.search_players(club="Santos", position="ST", limit=10)
        for p in players:
            assert p["Position"] == "ST"
            assert "santos" in p["_norm_club"]

    def test_top_brazilian_player_is_highly_rated(self, q):
        players = q.search_players(nationality="Brazil", limit=1)
        assert players[0]["Overall"] >= 85


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------

class TestFeatureCompetitionQueries:
    def test_standings_2019_brasileirao(self, q):
        """Scenario: Who won the 2019 Brasileirão?"""
        rows = q.standings("Brasileirão", 2019)
        assert rows
        assert rows[0]["points"] > rows[1]["points"]
        # Flamengo won the 2019 Brasileirão
        assert name_matches("Flamengo", rows[0]["team"])
        # full season: 38 matches for champion
        assert rows[0]["matches"] == 38

    def test_standings_format(self, q):
        rows = q.standings("Brasileirão", 2019)
        text = q.format_standings(rows, "Brasileirão", 2019)
        assert "Champion" in text
        assert "Flamengo" in text

    def test_standings_points_math(self, q):
        rows = q.standings("Brasileirão", 2019)
        for r in rows:
            assert r["points"] == r["wins"] * 3 + r["draws"]

    def test_standings_unknown_season(self, q):
        assert q.standings("Brasileirão", 1901) == []


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------

class TestFeatureStatisticalAnalysis:
    def test_average_goals_per_match(self, q):
        s = q.competition_stats(competition="Brasileirão")
        assert s["matches"] > 3000
        assert 1.5 < s["avg_goals_per_match"] < 4.0

    def test_home_win_rate_plausible(self, q):
        s = q.competition_stats(competition="Brasileirão")
        assert 30 < s["home_win_rate"] < 65

    def test_home_advantage(self, q):
        s = q.competition_stats(competition="Brasileirão")
        assert s["home_wins"] > s["away_wins"]

    def test_biggest_wins(self, q):
        """Scenario: Show me the biggest wins in the dataset."""
        wins = q.biggest_wins(limit=5)
        assert wins
        margins = [abs(m.home_goal - m.away_goal) for m in wins]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5

    def test_best_home_record(self, q):
        ranked = q.best_team_record(venue="home", min_matches=30)
        assert ranked
        assert ranked[0]["win_rate"] >= ranked[-1]["win_rate"]

    def test_biggest_wins_format(self, q):
        text = q.format_biggest_wins(q.biggest_wins(limit=3))
        assert text.count("\n") >= 3


# ---------------------------------------------------------------------------
# Feature: Data quality (normalization)
# ---------------------------------------------------------------------------

class TestFeatureNameAndDateNormalization:
    def test_state_suffix_matching(self):
        # a suffixed dataset name matches a plain query...
        assert name_matches("Palmeiras", "Palmeiras-SP")
        assert name_matches("Palmeiras", "Palmeiras")
        # ...and a suffixed query matches only its own team
        assert name_matches("Palmeiras-SP", "Palmeiras-SP")
        assert not name_matches("Palmeiras-SP", "Palmeiras-RJ")

    def test_ambiguous_teams_stay_distinct(self):
        # Atlético-MG and Atlético-PR must not be merged
        assert not name_matches("Atletico-MG", "Atletico-PR")
        assert name_matches("Atletico-MG", "Atletico-MG")
        assert name_matches("Atletico", "Atletico-MG")
        assert name_matches("Atletico", "Atletico-PR")

    def test_accents_are_normalized(self):
        assert normalize_name("Grêmio") == "gremio"
        assert normalize_name("São Paulo") == "sao paulo"
        assert name_matches("Gremio", "Grêmio-RS")

    def test_parenthetical_notes_removed(self):
        assert normalize_name("Nacional (URU)") == "nacional"
        assert name_matches("Barcelona", "Barcelona-EQU")

    def test_team_with_suffix_matches_plain(self, data):
        matches = data.team_matches("Palmeiras")
        assert len(matches) > 500
        for m in matches[:50]:
            assert name_matches("Palmeiras", m.home) or name_matches("Palmeiras", m.away)

    def test_multiple_date_formats(self):
        assert parse_date("2023-09-24").year == 2023
        assert parse_date("2012-05-19 18:30:00").month == 5
        assert parse_date("29/03/2003").day == 29
        assert parse_date("") is None
        assert parse_date("garbage") is None

    def test_utf8_names_handled(self, data):
        """Accented team names (Grêmio, Avaí) load correctly."""
        matches = data.team_matches("Grêmio")
        assert len(matches) > 100


# ---------------------------------------------------------------------------
# Feature: MCP server surface
# ---------------------------------------------------------------------------

class TestFeatureMCPServer:
    def test_server_exposes_tools(self):
        import server

        tools = asyncio.run(server.mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "find_matches",
            "head_to_head",
            "last_match_between",
            "team_stats",
            "compare_teams",
            "standings",
            "champion",
            "search_players",
            "top_players_at_club",
            "team_competitions",
            "competition_stats",
            "biggest_wins",
            "best_team_record",
            "dataset_overview",
        }
        assert expected <= names, f"missing tools: {expected - names}"

    def test_call_tool_over_in_memory_session(self):
        import server
        from mcp.shared.memory import create_connected_server_and_client_session

        async def run():
            async with create_connected_server_and_client_session(server.mcp) as client:
                await client.initialize()
                r = await client.call_tool("champion", {"competition": "Brasileirão", "season": 2019})
                return r.content[0].text

        text = asyncio.run(run())
        assert "Flamengo" in text
        assert "90 pts" in text


# ---------------------------------------------------------------------------
# Feature: Query performance
# ---------------------------------------------------------------------------

class TestFeatureQueryPerformance:
    def test_simple_lookup_under_2_seconds(self, q):
        start = time.perf_counter()
        q.find_matches(team="Flamengo", opponent="Fluminense")
        assert time.perf_counter() - start < 2.0

    def test_aggregate_query_under_5_seconds(self, q):
        start = time.perf_counter()
        q.standings("Brasileirão", 2019)
        q.competition_stats(competition="Brasileirão")
        assert time.perf_counter() - start < 5.0
