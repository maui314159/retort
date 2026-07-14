"""
BDD-style tests for the Brazilian Soccer MCP server tools.

Each test exercises an observable behaviour end-to-end using the tool
functions directly (no subprocess / network required).
"""

import json
import pytest

# Import tools directly – they are plain Python functions decorated by FastMCP.
from server import (
    search_matches,
    get_team_stats,
    get_standings,
    get_biggest_wins,
    get_competition_stats,
    search_players,
    get_best_teams,
    list_competitions,
)


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Scenario: Find matches between two teams."""

    def test_head_to_head_returns_matches(self):
        """
        Given the match data is loaded
        When I search for matches between "Flamengo" and "Fluminense"
        Then I should receive a list of matches
        And each match should have date, scores, and competition
        """
        result = json.loads(search_matches(team="Flamengo", team2="Fluminense"))
        assert result["total_found"] > 0
        assert len(result["matches"]) > 0
        first = result["matches"][0]
        assert "date" in first
        assert "home_goal" in first
        assert "away_goal" in first
        assert "competition" in first

    def test_head_to_head_summary_included(self):
        """Head-to-head summary should list wins for each team and draws."""
        result = json.loads(search_matches(team="Palmeiras", team2="Santos"))
        assert "head_to_head" in result
        h2h = result["head_to_head"]
        assert "Palmeiras_wins" in h2h
        assert "Santos_wins" in h2h
        assert "draws" in h2h

    def test_team_filter_returns_only_that_team(self):
        """Every returned match should involve the queried team."""
        result = json.loads(search_matches(team="Corinthians"))
        for m in result["matches"]:
            teams = (m["home_team"].lower() + " " + m["away_team"].lower())
            assert "corinthians" in teams

    def test_season_filter_narrows_results(self):
        """Matches filtered by season should all be from that year."""
        result = json.loads(search_matches(team="Flamengo", season=2019))
        for m in result["matches"]:
            assert m["season"] == 2019

    def test_competition_filter_brasileirao(self):
        """Competition filter should restrict to Brasileirao."""
        result = json.loads(search_matches(competition="Brasileirao", season=2019, limit=10))
        for m in result["matches"]:
            assert m["competition"] == "Brasileirao"

    def test_competition_filter_copa_do_brasil(self):
        result = json.loads(search_matches(competition="Copa do Brasil", limit=10))
        assert result["total_found"] > 0
        for m in result["matches"]:
            assert m["competition"] == "Copa do Brasil"

    def test_competition_filter_libertadores(self):
        result = json.loads(search_matches(competition="Copa Libertadores", limit=5))
        assert result["total_found"] > 0

    def test_date_range_filter(self):
        """Matches returned should respect date_from and date_to."""
        result = json.loads(search_matches(
            date_from="2023-01-01",
            date_to="2023-12-31",
            limit=20,
        ))
        for m in result["matches"]:
            assert m["date"].startswith("2023")

    def test_limit_respected(self):
        result = json.loads(search_matches(limit=5))
        assert len(result["matches"]) <= 5


# ---------------------------------------------------------------------------
# Feature: Team Statistics
# ---------------------------------------------------------------------------

class TestTeamStats:
    """Scenario: Get team statistics."""

    def test_basic_stats_keys_present(self):
        """
        Given the match data is loaded
        When I request statistics for "Palmeiras" in season "2023"
        Then I should receive wins, losses, draws, and goals
        """
        result = json.loads(get_team_stats(team="Palmeiras", season=2023))
        for key in ("wins", "draws", "losses", "goals_for", "goals_against",
                    "total_matches", "win_rate_pct"):
            assert key in result, f"Missing key: {key}"

    def test_stats_math_consistency(self):
        """Wins + draws + losses must equal total_matches."""
        result = json.loads(get_team_stats(team="Corinthians"))
        assert result["wins"] + result["draws"] + result["losses"] == result["total_matches"]

    def test_home_only_flag(self):
        """home_only=True should yield only home matches."""
        result_all = json.loads(get_team_stats(team="Flamengo", season=2019))
        result_home = json.loads(get_team_stats(team="Flamengo", season=2019, home_only=True))
        # Home matches ≤ all matches
        assert result_home["total_matches"] <= result_all["total_matches"]
        # Home wins match nested home.wins
        assert result_home["wins"] == result_home["home"]["wins"]

    def test_away_only_flag(self):
        result = json.loads(get_team_stats(team="Gremio", away_only=True))
        assert result["total_matches"] == result["away"]["matches"]

    def test_unknown_team_returns_error(self):
        result = json.loads(get_team_stats(team="ZZZUnknownTeamXXX"))
        assert "error" in result

    def test_points_calculation(self):
        """Points = wins * 3 + draws."""
        result = json.loads(get_team_stats(team="Santos", season=2019,
                                           competition="Brasileirao"))
        expected_pts = result["wins"] * 3 + result["draws"]
        assert result["points"] == expected_pts


# ---------------------------------------------------------------------------
# Feature: League Standings
# ---------------------------------------------------------------------------

class TestStandings:
    """Scenario: Calculate standings from match results."""

    def test_standings_have_all_teams(self):
        """
        Given Brasileirao 2019 match data
        When I request standings
        Then I should get a sorted list of teams with points
        """
        result = json.loads(get_standings(season=2019, competition="Brasileirao"))
        assert "standings" in result
        standings = result["standings"]
        assert len(standings) >= 10  # Brazilian top flight has 20 teams

    def test_standings_sorted_by_points(self):
        """Table should be in descending order of points."""
        result = json.loads(get_standings(season=2019, competition="Brasileirao"))
        pts = [row["Pts"] for row in result["standings"]]
        assert pts == sorted(pts, reverse=True)

    def test_standings_has_position_field(self):
        result = json.loads(get_standings(season=2019))
        assert result["standings"][0]["position"] == 1

    def test_standings_math(self):
        """For each team: W + D + L = P."""
        result = json.loads(get_standings(season=2018))
        for row in result["standings"]:
            assert row["W"] + row["D"] + row["L"] == row["P"]

    def test_standings_unknown_season(self):
        result = json.loads(get_standings(season=1800))
        assert "error" in result

    def test_flamengo_champions_2019(self):
        """Flamengo won Brasileirao 2019; they should be top."""
        result = json.loads(get_standings(season=2019))
        leader = result["standings"][0]["team"].lower()
        assert "flamengo" in leader


# ---------------------------------------------------------------------------
# Feature: Biggest Wins
# ---------------------------------------------------------------------------

class TestBiggestWins:
    """Scenario: Retrieve matches with largest goal margins."""

    def test_results_sorted_by_margin(self):
        result = json.loads(get_biggest_wins(limit=10))
        margins = [m["margin"] for m in result["biggest_wins"]]
        assert margins == sorted(margins, reverse=True)

    def test_margin_matches_score(self):
        """margin field should equal |home_goal - away_goal| from score."""
        result = json.loads(get_biggest_wins(limit=5))
        for m in result["biggest_wins"]:
            parts = m["score"].split("-")
            diff = abs(int(parts[0]) - int(parts[1]))
            assert diff == m["margin"]

    def test_filter_by_competition(self):
        result = json.loads(get_biggest_wins(competition="Brasileirao", limit=5))
        assert len(result["biggest_wins"]) > 0

    def test_filter_by_season(self):
        result = json.loads(get_biggest_wins(season=2019, limit=5))
        for m in result["biggest_wins"]:
            assert m["season"] == 2019


# ---------------------------------------------------------------------------
# Feature: Competition Statistics
# ---------------------------------------------------------------------------

class TestCompetitionStats:
    """Scenario: Aggregate statistics for a competition."""

    def test_avg_goals_reasonable(self):
        """Average goals per match in Brazilian football should be ~2-3."""
        result = json.loads(get_competition_stats(competition="Brasileirao"))
        avg = result["avg_goals_per_match"]
        assert 1.0 < avg < 6.0

    def test_home_win_rate_reasonable(self):
        """Home win rate is typically 40-60%."""
        result = json.loads(get_competition_stats(competition="Brasileirao"))
        hwr = result["home_win_rate_pct"]
        assert 25.0 < hwr < 70.0

    def test_rates_sum_to_100(self):
        """home_win + away_win + draw rates should equal 100%."""
        result = json.loads(get_competition_stats(competition="Brasileirao",
                                                  season=2019))
        total = round(
            result["home_win_rate_pct"]
            + result["away_win_rate_pct"]
            + result["draw_rate_pct"],
            0,
        )
        assert total == 100.0

    def test_no_filter_covers_all(self):
        """Without filters, total_matches should equal full dataset."""
        from data_loader import load_all_matches
        df = load_all_matches()
        result = json.loads(get_competition_stats())
        assert result["total_matches"] == len(df)

    def test_season_filter(self):
        result = json.loads(get_competition_stats(season=2022))
        for s in result["seasons_covered"]:
            assert s == 2022


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    """Scenario: Search player database."""

    def test_search_by_name(self):
        """
        Given the player data is loaded
        When I search for "Neymar"
        Then I should find at least one player named Neymar
        """
        result = json.loads(search_players(name="Neymar"))
        assert result["total_found"] > 0
        assert any("neymar" in p["Name"].lower() for p in result["players"])

    def test_search_brazilian_players(self):
        """Nationality='Brazil' should return many players."""
        result = json.loads(search_players(nationality="Brazil", limit=50))
        assert result["total_found"] > 100

    def test_search_by_club(self):
        result = json.loads(search_players(club="Fluminense"))
        assert result["total_found"] > 0
        for p in result["players"]:
            assert "fluminense" in p["Club"].lower()

    def test_search_by_position(self):
        result = json.loads(search_players(position="GK", limit=10))
        for p in result["players"]:
            assert "GK" in p["Position"]

    def test_min_overall_filter(self):
        result = json.loads(search_players(min_overall=85, limit=20))
        for p in result["players"]:
            assert p["Overall"] >= 85

    def test_results_sorted_by_overall_desc(self):
        result = json.loads(search_players(nationality="Brazil", limit=20))
        overalls = [p["Overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_combined_filters(self):
        result = json.loads(search_players(nationality="Brazil", position="ST",
                                           min_overall=70, limit=10))
        for p in result["players"]:
            assert p["Overall"] >= 70
            assert p["Nationality"] == "Brazil"

    def test_unknown_player_empty(self):
        result = json.loads(search_players(name="ZZZNoSuchPlayerXXX"))
        assert result["total_found"] == 0

    def test_limit_respected(self):
        result = json.loads(search_players(nationality="Brazil", limit=5))
        assert len(result["players"]) <= 5


# ---------------------------------------------------------------------------
# Feature: Best Teams Ranking
# ---------------------------------------------------------------------------

class TestBestTeams:
    """Scenario: Rank teams by various metrics."""

    def test_rank_by_win_rate(self):
        result = json.loads(get_best_teams(competition="Brasileirao", season=2019,
                                           metric="win_rate", limit=5))
        rates = [t["win_rate"] for t in result["teams"]]
        assert rates == sorted(rates, reverse=True)

    def test_rank_by_goals_scored(self):
        result = json.loads(get_best_teams(competition="Brasileirao", season=2019,
                                           metric="goals_scored", limit=5))
        goals = [t["goals_for"] for t in result["teams"]]
        assert goals == sorted(goals, reverse=True)

    def test_rank_by_away_win_rate(self):
        result = json.loads(get_best_teams(competition="Brasileirao", season=2019,
                                           metric="away_win_rate", limit=5))
        assert len(result["teams"]) > 0

    def test_limit_respected(self):
        result = json.loads(get_best_teams(limit=3))
        assert len(result["teams"]) <= 3


# ---------------------------------------------------------------------------
# Feature: List Competitions
# ---------------------------------------------------------------------------

class TestListCompetitions:
    """Scenario: Enumerate available competitions."""

    def test_contains_brasileirao(self):
        result = json.loads(list_competitions())
        assert "Brasileirao" in result["competitions"]

    def test_contains_copa_do_brasil(self):
        result = json.loads(list_competitions())
        assert "Copa do Brasil" in result["competitions"]

    def test_contains_libertadores(self):
        result = json.loads(list_competitions())
        assert "Copa Libertadores" in result["competitions"]

    def test_each_competition_has_matches(self):
        result = json.loads(list_competitions())
        for comp, info in result["competitions"].items():
            assert info["matches"] > 0

    def test_each_competition_has_seasons(self):
        result = json.loads(list_competitions())
        for comp, info in result["competitions"].items():
            assert len(info["seasons"]) > 0
