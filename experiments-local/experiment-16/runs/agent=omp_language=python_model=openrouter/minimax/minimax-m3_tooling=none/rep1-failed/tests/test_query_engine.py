"""
test_query_engine.py
====================

Unit tests for the high-level query functions in ``query_engine``.
"""

from __future__ import annotations

import pytest

import data_loader
import query_engine


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    data_loader.clear_cache()
    yield
    data_loader.clear_cache()


# ---------------------------------------------------------------------------
# search_matches
# ---------------------------------------------------------------------------


def test_search_matches_two_teams_returns_count_and_matches() -> None:
    result = query_engine.search_matches(
        team="Flamengo", opponent="Fluminense", season=2023, limit=10
    )
    assert result["count"] > 0
    assert result["returned"] > 0
    for match in result["matches"]:
        assert match["home_goal"] is not None
        assert match["away_goal"] is not None


def test_search_matches_team_only() -> None:
    result = query_engine.search_matches(team="Flamengo", season=2023, limit=5)
    assert result["count"] > 0
    for match in result["matches"]:
        assert "Flamengo" in match["home_team"] or "Flamengo" in match["away_team"]


def test_search_matches_venue_filter() -> None:
    home = query_engine.search_matches(team="Flamengo", venue="home", season=2023)
    away = query_engine.search_matches(team="Flamengo", venue="away", season=2023)
    assert home["count"] > 0
    assert away["count"] > 0
    for m in home["matches"]:
        assert "Flamengo" in m["home_team"]
    for m in away["matches"]:
        assert "Flamengo" in m["away_team"]


def test_search_matches_unknown_team() -> None:
    result = query_engine.search_matches(team="Nonexistent FC")
    assert result["count"] == 0
    assert "Could not resolve" in result.get("message", "")


def test_search_matches_date_range() -> None:
    result = query_engine.search_matches(
        team="Flamengo", date_from="2023-01-01", date_to="2023-12-31", limit=50
    )
    assert result["count"] > 0


# ---------------------------------------------------------------------------
# get_team_stats
# ---------------------------------------------------------------------------


def test_get_team_stats_returns_expected_keys() -> None:
    result = query_engine.get_team_stats("Palmeiras", season=2022)
    for key in (
        "team",
        "team_key",
        "matches",
        "wins",
        "draws",
        "losses",
        "goals_for",
        "goals_against",
        "goal_difference",
        "win_rate",
    ):
        assert key in result


def test_get_team_stats_consistency() -> None:
    result = query_engine.get_team_stats("Palmeiras", season=2022)
    assert result["matches"] == result["wins"] + result["draws"] + result["losses"]
    assert result["goal_difference"] == result["goals_for"] - result["goals_against"]


def test_get_team_stats_unknown_team() -> None:
    result = query_engine.get_team_stats("Nonexistent FC")
    assert "error" in result


# ---------------------------------------------------------------------------
# get_head_to_head
# ---------------------------------------------------------------------------


def test_get_head_to_head_returns_matches() -> None:
    result = query_engine.get_head_to_head("Flamengo", "Fluminense", season=2023)
    assert "matches" in result
    assert "summary" in result
    assert result["count"] > 0


def test_get_head_to_head_summary_totals_match_count() -> None:
    result = query_engine.get_head_to_head("Palmeiras", "Corinthians", season=2023)
    summary = result["summary"]
    assert summary["total"] == result["count"]


# ---------------------------------------------------------------------------
# search_players
# ---------------------------------------------------------------------------


def test_search_players_by_nationality() -> None:
    result = query_engine.search_players(nationality="Brazil", limit=5)
    assert result["count"] > 0
    for p in result["players"]:
        assert p["nationality"] == "Brazil"


def test_search_players_by_club() -> None:
    result = query_engine.search_players(club="Real Madrid", limit=5)
    assert result["count"] > 0
    for p in result["players"]:
        assert "Real Madrid" in p["club"]


def test_search_players_min_overall() -> None:
    result = query_engine.search_players(min_overall=88, limit=10)
    for p in result["players"]:
        assert p["overall"] >= 88


# ---------------------------------------------------------------------------
# get_standings
# ---------------------------------------------------------------------------


def test_get_standings_2019_has_20_teams() -> None:
    result = query_engine.get_standings("Brasileirão", 2019)
    assert len(result["standings"]) == 20


def test_get_standings_sorted_by_points() -> None:
    result = query_engine.get_standings("Brasileirão", 2022)
    points = [t["points"] for t in result["standings"]]
    assert points == sorted(points, reverse=True)


def test_get_standings_no_data() -> None:
    result = query_engine.get_standings("Brasileirão", 1900)
    assert result["standings"] == []
    assert "message" in result


# ---------------------------------------------------------------------------
# get_relegated_teams
# ---------------------------------------------------------------------------


def test_get_relegated_teams_2019() -> None:
    result = query_engine.get_relegated_teams(2019)
    assert len(result["relegated"]) == 4
    positions = [t["position"] for t in result["relegated"]]
    assert positions == sorted(positions)


def test_get_relegated_teams_no_data() -> None:
    result = query_engine.get_relegated_teams(1900)
    assert result["relegated"] == []


# ---------------------------------------------------------------------------
# get_biggest_wins
# ---------------------------------------------------------------------------


def test_get_biggest_wins_ordered_by_difference() -> None:
    result = query_engine.get_biggest_wins("Brasileirão", 2022, limit=5)
    diffs = [m["goal_difference"] for m in result["matches"]]
    assert diffs == sorted(diffs, reverse=True)


# ---------------------------------------------------------------------------
# get_goals_per_match
# ---------------------------------------------------------------------------


def test_get_goals_per_match_2023() -> None:
    result = query_engine.get_goals_per_match("Brasileirão", 2023)
    assert result["total_matches"] > 0
    assert result["total_goals"] > 0
    # home_wins + draws + away_wins == total_matches
    assert result["home_wins"] + result["draws"] + result["away_wins"] == result["total_matches"]


# ---------------------------------------------------------------------------
# get_top_scoring_teams
# ---------------------------------------------------------------------------


def test_get_top_scoring_teams_2023() -> None:
    result = query_engine.get_top_scoring_teams("Brasileirão", 2023, limit=5)
    goals = [t["goals"] for t in result["teams"]]
    assert goals == sorted(goals, reverse=True)


# ---------------------------------------------------------------------------
# get_team_competition_history
# ---------------------------------------------------------------------------


def test_get_team_competition_history_flamengo() -> None:
    result = query_engine.get_team_competition_history("Flamengo")
    assert "competitions" in result
    assert len(result["competitions"]) > 0


# ---------------------------------------------------------------------------
# brazilian_club_summary
# ---------------------------------------------------------------------------


def test_brazilian_club_summary_finds_santos() -> None:
    result = query_engine.brazilian_club_summary()
    assert result["count"] > 0
    club_names = [c["club"] for c in result["clubs"]]
    assert "Santos" in club_names
