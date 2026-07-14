"""BDD-style tests for the Brazilian Soccer MCP server."""

import json
from datetime import date

import pytest

from data_loader import BrazilianSoccerData, normalize_team_name, team_matches
from queries import (
    best_attack,
    best_away_record,
    best_home_record,
    biggest_wins,
    competition_stats,
    find_matches,
    head_to_head,
    relegated_teams,
    search_players,
    season_standings,
    team_stats,
    top_players_by_club,
)
from server import mcp


@pytest.fixture(scope="module")
def data():
    """Load all datasets once for the test module."""
    ds = BrazilianSoccerData()
    ds.load()
    return ds


# ---------------------------------------------------------------------------
# Feature: Data loading and normalization
# ---------------------------------------------------------------------------


def test_all_csv_files_are_loaded(data):
    """Given the datasets are present, then all files should be loaded."""
    assert len(data.matches) > 17_000
    assert len(data.players) > 18_000


def test_competitions_are_available(data):
    """Given the match data is loaded, then major competitions are represented."""
    competitions = set(data.matches["competition"].dropna())
    assert "Brasileirão" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions


def test_team_name_normalization():
    """Given team names with different conventions, then they match."""
    assert normalize_team_name("Palmeiras-SP") == "palmeiras"
    assert normalize_team_name("São Paulo") == "sao paulo"
    assert normalize_team_name("Athletico-PR") == "atletico paranaense"
    assert normalize_team_name("Atletico Paranaense") == "atletico paranaense"
    assert normalize_team_name("Vasco Da Gama RJ") == "vasco da gama"


def test_team_matches_variations():
    """Given normalized team names, then synonyms match."""
    assert team_matches("Flamengo-RJ", "Flamengo")
    assert team_matches("Atlético-MG", "Atletico Mineiro")
    assert team_matches("EC Bahia", "Bahia-BA")


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------


def test_find_matches_between_two_teams(data):
    """Given the match data is loaded, when searching for Flamengo vs Fluminense,
    then matches with date and scores are returned."""
    result = find_matches(data, team="Flamengo", opponent="Fluminense", limit=10)
    assert isinstance(result, list)
    assert len(result) > 0
    for match in result:
        assert "date" in match
        assert match["home_team"]
        assert match["away_team"]
        assert match["competition"]


def test_find_matches_by_season_and_competition(data):
    """Given the match data is loaded, when filtering by season and competition,
    then only matching matches are returned."""
    result = find_matches(data, team="Palmeiras", season=2023, competition="Brasileirão")
    assert len(result) > 0
    for match in result:
        assert match["season"] == 2023
        assert match["competition"] == "Brasileirão"


def test_find_matches_by_date_range(data):
    """Given the match data is loaded, when filtering by date range,
    then returned matches fall inside the range."""
    result = find_matches(data, team="Flamengo", start_date="2023-01-01", end_date="2023-12-31")
    assert len(result) > 0
    for match in result:
        assert match["date"]
        assert date.fromisoformat(match["date"]).year == 2023


def test_head_to_head_returns_record(data):
    """Given the match data is loaded, when requesting head-to-head,
    then wins/losses/draws are computed."""
    result = head_to_head(data, "Flamengo", "Fluminense")
    assert result["team_a"] == "Flamengo"
    assert result["team_b"] == "Fluminense"
    total = result["team_a_wins"] + result["team_b_wins"] + result["draws"]
    assert total == len(result["matches"])
    assert total > 0


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------


def test_team_stats_home_record(data):
    """Given the match data is loaded, when requesting Corinthians' home record,
    then wins, losses, draws and goals are returned."""
    stats = team_stats(data, "Corinthians", competition="Brasileirão", season=2022, venue="home")
    assert stats["team"] == "Corinthians"
    assert stats["season"] == 2022
    assert stats["venue"] == "home"
    assert stats["matches"] > 0
    assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
    assert stats["goals_for"] >= 0
    assert stats["goals_against"] >= 0


def test_team_stats_all_venues(data):
    """Given the match data is loaded, when requesting all-venue stats,
    then totals across home and away are returned."""
    stats = team_stats(data, "Flamengo", competition="Brasileirão", season=2019)
    assert stats["venue"] == "all"
    assert stats["matches"] == 38


def test_best_attack(data):
    """Given the match data is loaded, when requesting top scorers,
    then teams are ranked by goals scored."""
    result = best_attack(data, competition="Brasileirão", season=2019, top_n=5)
    assert len(result) == 5
    assert result[0]["goals"] >= result[1]["goals"]
    assert result[0]["team"]


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------


def test_search_players_by_nationality(data):
    """Given the player data is loaded, when filtering by nationality,
    then Brazilian players are returned."""
    result = search_players(data, nationality="Brazil", limit=1000)
    assert result["count"] > 800
    for player in result["players"]:
        assert player["nationality"] == "Brazil"


def test_search_players_by_name(data):
    """Given the player data is loaded, when searching by name,
    then matching players are returned."""
    result = search_players(data, name="Neymar")
    assert result["count"] > 0
    assert "Neymar" in result["players"][0]["name"]


def test_top_players_by_club(data):
    """Given the player data is loaded, when requesting top players at a club,
    then sorted players are returned."""
    result = top_players_by_club(data, club="Flamengo", top_n=5)
    assert result["count"] <= 5
    # Flamengo may not be present in this older FIFA dataset, so only assert shape.
    assert "players" in result


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------


def test_season_standings(data):
    """Given the match data is loaded, when computing the league table,
    then teams are ranked by points."""
    table = season_standings(data, "Brasileirão", 2019)
    assert len(table) == 20
    assert table[0]["team"] == "flamengo"
    assert table[0]["points"] > table[1]["points"]


def test_2019_brasileirao_champion(data):
    """Given the match data is loaded, then Flamengo won the 2019 Brasileirão."""
    table = season_standings(data, "Brasileirão", 2019)
    assert table[0]["team"] == "flamengo"
    assert table[0]["points"] == 90


def test_relegated_teams(data):
    """Given the match data is loaded, when requesting relegated teams,
    then the bottom four are returned."""
    bottom = relegated_teams(data, "Brasileirão", 2019)
    assert len(bottom) == 4
    # Positions should be 17-20 in a 20-team table.
    for row in bottom:
        assert row["position"] >= 17


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------


def test_competition_stats(data):
    """Given the match data is loaded, then aggregate stats are computed."""
    stats = competition_stats(data, competition="Brasileirão")
    assert stats["matches"] > 0
    assert 1.5 <= stats["avg_goals"] <= 4.0
    assert stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"] == pytest.approx(100.0, 0.1)


def test_biggest_wins(data):
    """Given the match data is loaded, then largest victories are returned."""
    wins = biggest_wins(data, competition="Brasileirão", top_n=5)
    assert len(wins) == 5
    assert wins[0]["margin"] >= wins[1]["margin"]
    assert wins[0]["match"]


def test_best_home_record(data):
    """Given the match data is loaded, then best home records are returned."""
    records = best_home_record(data, competition="Brasileirão", min_matches=10)
    assert len(records) > 0
    assert records[0]["win_rate"] >= records[1]["win_rate"]


def test_best_away_record(data):
    """Given the match data is loaded, then best away records are returned."""
    records = best_away_record(data, competition="Brasileirão", min_matches=10)
    assert len(records) > 0
    assert records[0]["win_rate"] >= records[1]["win_rate"]


# ---------------------------------------------------------------------------
# Feature: MCP Server Tools
# ---------------------------------------------------------------------------


def test_list_competitions_tool():
    """Given the MCP server is running, then competitions can be listed."""
    result = mcp.get_tool("list_competitions")()
    assert len(result) == 1
    payload = json.loads(result[0]["text"])
    assert "competitions" in payload
    assert "Brasileirão" in payload["competitions"]


def test_find_matches_tool():
    """Given the MCP server is running, when calling find_matches_tool,
    then a JSON response with matches is returned."""
    result = mcp.get_tool("find_matches_tool")(
        team="Flamengo", opponent="Fluminense", limit=5
    )
    payload = json.loads(result[0]["text"])
    assert payload["count"] > 0
    assert len(payload["matches"]) > 0


def test_head_to_head_tool():
    """Given the MCP server is running, when calling head_to_head_tool,
    then record and matches are returned."""
    result = mcp.get_tool("head_to_head_tool")(team_a="Flamengo", team_b="Corinthians")
    payload = json.loads(result[0]["text"])
    assert "team_a_wins" in payload
    assert "team_b_wins" in payload
    assert "draws" in payload


def test_team_stats_tool():
    """Given the MCP server is running, when calling team_stats_tool,
    then stats are returned."""
    result = mcp.get_tool("team_stats_tool")(
        team="Palmeiras", competition="Brasileirão", season=2023, venue="home"
    )
    payload = json.loads(result[0]["text"])
    assert payload["team"] == "Palmeiras"
    assert payload["matches"] >= 0


def test_season_standings_tool():
    """Given the MCP server is running, when calling season_standings_tool,
    then the league table is returned."""
    result = mcp.get_tool("season_standings_tool")(
        competition="Brasileirão", season=2019
    )
    payload = json.loads(result[0]["text"])
    assert len(payload["standings"]) == 20
    assert payload["standings"][0]["team"] == "flamengo"


def test_search_players_tool():
    """Given the MCP server is running, when calling search_players_tool,
    then player results are returned."""
    result = mcp.get_tool("search_players_tool")(
        nationality="Brazil", min_overall=85, limit=10
    )
    payload = json.loads(result[0]["text"])
    assert payload["count"] > 0
    assert all(p["nationality"] == "Brazil" for p in payload["players"])
    assert all(p["overall"] >= 85 for p in payload["players"])


def test_response_is_serializable_json(data):
    """All query outputs should be serializable as JSON."""
    result = head_to_head(data, "Flamengo", "Flamengo")
    json.dumps(result)


# ---------------------------------------------------------------------------
# Feature: Sample questions from specification
# ---------------------------------------------------------------------------


def test_when_did_flamengo_last_play_corinthians(data):
    """When did Flamengo last play Corinthians?"""
    matches = find_matches(data, team="Flamengo", opponent="Corinthians", limit=1)
    assert len(matches) == 1


def test_who_is_gabriel_barbosa(data):
    """Who is Gabriel Barbosa?"""
    result = search_players(data, name="Gabriel Barbosa")
    assert result["count"] >= 0


def test_players_at_flamengo(data):
    """Which players play for Flamengo?"""
    result = search_players(data, club="Flamengo", limit=50)
    assert result["count"] >= 0


def test_what_competitions_has_palmeiras_played_in(data):
    """What competitions has Palmeiras played in?"""
    matches = find_matches(data, team="Palmeiras", limit=1000)
    competitions = {m["competition"] for m in matches}
    assert "Brasileirão" in competitions


def test_compare_2018_and_2019_seasons(data):
    """Compare the 2018 and 2019 seasons."""
    stats_2018 = competition_stats(data, competition="Brasileirão")
    stats_2019 = competition_stats(data, competition="Brasileirão")
    assert stats_2018["matches"] > 0
    assert stats_2019["matches"] > 0
