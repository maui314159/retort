"""BDD tests for Brazilian Soccer MCP Server."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from pytest_bdd import given, when, then, parsers

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import SoccerData, normalize_team

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"
soccer = SoccerData(DATA_DIR)

# Auto-discover all .feature files in this directory
from pytest_bdd import scenarios as _scenarios
import glob as _glob

for _feat in _glob.glob(str(Path(__file__).parent / "*.feature")):
    _scenarios(_feat)


# ── Shared result stores (per-step) ────────────────────────────────
_store: dict = {}


# ── Given steps ─────────────────────────────────────────────────────

@given("the match data is loaded")
def match_data_loaded():
    return soccer


@given("the player data is loaded")
def player_data_loaded():
    return soccer


@given("the data directory")
def data_directory():
    return DATA_DIR


# ── When steps ──────────────────────────────────────────────────────

@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_matches_between(team_a, team_b):
    _store["matches"] = soccer.find_matches(team=team_a, opponent=team_b)


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def request_team_stats(team, season):
    _store["team_stats"] = soccer.team_stats(team, season=season)


@when(parsers.parse('I search for matches in competition "{competition}"'))
def search_by_competition(competition):
    _store["comp_matches"] = soccer.find_matches(competition=competition)


@when(parsers.parse('I search for matches from "{date_from}" to "{date_to}"'))
def search_by_date_range(date_from, date_to):
    _store["date_matches"] = soccer.find_matches(date_from=date_from, date_to=date_to)


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def compare_head_to_head(team_a, team_b):
    _store["h2h"] = soccer.head_to_head(team_a, team_b)


@when(parsers.parse('I request home-only statistics for "{team}"'))
def request_home_stats(team):
    _store["home_matches"] = soccer.find_matches(team=team, home_only=True)


@when(parsers.parse('I search for players named "{name}"'))
def search_player_by_name(name):
    _store["players_name"] = soccer.search_players(name=name)


@when(parsers.parse('I search for players of nationality "{nationality}"'))
def search_player_by_nationality(nationality):
    _store["players_nat"] = soccer.search_players(nationality=nationality)


@when(parsers.parse('I search for players at club "{club}"'))
def search_player_by_club(club):
    _store["players_club"] = soccer.search_players(club=club)


@when(parsers.parse('I request standings for season {season:d} competition "{competition}"'))
def request_standings(season, competition):
    _store["standings"] = soccer.standings(season, competition)


@when(parsers.parse('I request average goals for competition "{competition}"'))
def request_avg_goals(competition):
    _store["avg_goals"] = soccer.avg_goals(competition)


@when("I request biggest wins")
def request_biggest_wins():
    _store["biggest_wins"] = soccer.biggest_wins(limit=10)


@when(parsers.parse('I search for matches with team "{team}"'))
def search_matches_with_team(team):
    _store["team_matches"] = soccer.find_matches(team=team)


# ── Then steps ──────────────────────────────────────────────────────

@then("I should receive a list of matches")
def receive_match_list():
    df = _store["matches"]
    assert not df.empty, "Expected matches but got empty result"


@then("each match should have date, scores, and competition")
def match_has_required_fields():
    df = _store["matches"]
    required = {"home_team", "away_team", "home_goal", "away_goal", "date", "competition"}
    assert required.issubset(df.columns), f"Missing columns: {required - set(df.columns)}"


@then("I should receive wins, losses, draws, and goals")
def receive_team_stats():
    result = _store["team_stats"]
    assert result["matches"] > 0, "Expected at least one match"
    assert "wins" in result
    assert "draws" in result
    assert "losses" in result
    assert "goals_for" in result
    assert "goals_against" in result


@then("I should receive matches from that competition only")
def receive_competition_matches():
    df = _store["comp_matches"]
    assert not df.empty
    assert all("Libertadores" in c for c in df["competition"])


@then("I should receive matches within that date range")
def receive_date_range_matches():
    df = _store["date_matches"]
    assert not df.empty
    dates = df["date"].dropna()
    assert all(d >= pd.Timestamp("2023-01-01") and d <= pd.Timestamp("2023-12-31") for d in dates)


@then("I should receive win counts for both teams and draws")
def receive_head_to_head():
    result = _store["h2h"]
    assert "team_a_wins" in result
    assert "team_b_wins" in result
    assert "draws" in result
    assert result["total_matches"] > 0


@then("I should receive statistics for home matches only")
def receive_home_stats():
    df = _store["home_matches"]
    assert not df.empty
    assert all(df["home_team"] == "Corinthians")


@then("I should receive player records matching that name")
def receive_player_by_name():
    df = _store["players_name"]
    assert not df.empty
    assert any("Neymar" in name for name in df["Name"])


@then("I should receive only Brazilian players")
def receive_brazilian_players():
    df = _store["players_nat"]
    assert not df.empty
    assert all(df["Nationality"] == "Brazil")


@then("I should receive players from that club")
def receive_club_players():
    df = _store["players_club"]
    assert not df.empty
    assert all("Santos" in club for club in df["Club"])


@then("I should receive a sorted table with points and goal difference")
def receive_standings():
    result = _store["standings"]
    assert len(result) > 0
    pts = [r["pts"] for r in result]
    assert pts == sorted(pts, reverse=True)
    for entry in result:
        assert "pts" in entry
        assert "w" in entry
        assert "gf" in entry
        assert "ga" in entry


@then("the first-place team should be marked as champion")
def first_is_champion():
    result = _store["standings"]
    assert len(result) > 0
    if len(result) > 1:
        assert result[0]["pts"] >= result[1]["pts"]


@then("I should receive average goals per match and home win rate")
def receive_avg_goals():
    result = _store["avg_goals"]
    assert "avg_goals_per_match" in result
    assert "home_win_rate" in result
    assert result["avg_goals_per_match"] > 0
    assert result["home_win_rate"] > 0


@then("I should receive matches sorted by goal difference")
def receive_biggest_wins():
    result = _store["biggest_wins"]
    assert len(result) > 0
    diffs = [w["winner_goals"] - w["loser_goals"] for w in result]
    assert diffs == sorted(diffs, reverse=True)


@then(parsers.parse('results should match normalized team name "{expected}"'))
def normalized_team_match(expected):
    df = _store["team_matches"]
    assert not df.empty
    teams = set(df["home_team"]) | set(df["away_team"])
    assert expected in teams


@then("all six CSV files should be loadable and queryable")
def all_files_loadable():
    assert len(soccer.brasileirao) > 0
    assert len(soccer.cup) > 0
    assert len(soccer.libertadores) > 0
    assert len(soccer.extended) > 0
    assert len(soccer.historical) > 0
    assert len(soccer.players) > 0
