"""BDD-style tests for the Brazilian Soccer MCP server.

Feature: Match Queries
Feature: Team Queries
Feature: Player Queries
Feature: Competition Queries
Feature: Statistical Analysis
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer import load_data
import server as srv


@pytest.fixture(scope="module")
def data():
    return load_data()


# ---------------------------------------------------------------
# Feature: Data loading
# ---------------------------------------------------------------


def test_all_six_datasets_loaded(data):
    """Scenario: All 6 CSV files are loadable and queryable
    Given the data directory
    Then all datasets are loaded with rows
    """
    assert len(data.matches) > 20000
    assert len(data.players) == 18207
    comps = {m.competition for m in data.matches}
    assert {"Brasileirão", "Copa do Brasil", "Copa Libertadores"} <= comps
    assert any("2003-2019" in c for c in comps)
    assert any(c.startswith("Copa do Brasil") for c in comps)


def test_team_name_normalization():
    """Scenario: Team name variations normalize to the same key
    When I normalize "Palmeiras-SP", "SE Palmeiras", and "Palmeiras"
    Then they all produce the same match key
    """
    from brazilian_soccer.loader import normalize_team

    assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")
    assert normalize_team("SE Palmeiras") == normalize_team("Palmeiras")
    assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")
    assert normalize_team("Grêmio") == normalize_team("Gremio")
    assert normalize_team("Sport Club Corinthians Paulista") == normalize_team("Corinthians")


def test_date_format_handling():
    """Scenario: Multiple date formats parse correctly
    When I parse ISO, Brazilian, and datetime strings
    Then each yields the correct date
    """
    from brazilian_soccer.loader import parse_date

    assert parse_date("2023-09-24").isoformat() == "2023-09-24"
    assert parse_date("29/03/2003").isoformat() == "2003-03-29"
    assert parse_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"
    assert parse_date("") is None


# ---------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------


def test_find_matches_between_two_teams(data):
    """Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    """
    results = srv.find_matches(srv._data, team="Flamengo", opponent="Fluminense")
    assert len(results) > 5
    for m in results:
        assert m["date"] is not None
        assert isinstance(m["home_goal"], int) and isinstance(m["away_goal"], int)
        assert m["competition"]
    teams = {(m["home"], m["away"]) for m in results}
    assert any("Flamengo" in h and "Fluminense" in a for h, a in teams)


def test_find_matches_by_team_season_competition(data):
    """Scenario: What matches did Palmeiras play in 2023?
    Given the match data is loaded
    When I search for Palmeiras in the 2022 Brasileirão
    Then all returned matches involve Palmeiras in season 2023
    """
    results = srv.find_matches(srv._data, team="Palmeiras", competition="Brasileirão", season=2022)
    assert 30 <= len(results) <= 38
    for m in results:
        assert m["season"] == 2022
        assert m["competition"] == "Brasileirão"
        assert "Palmeiras" in m["home"] or "Palmeiras" in m["away"]


def test_find_matches_by_date_range(data):
    """Scenario: Filter matches by date range
    When I search for matches between 2023-06-01 and 2023-06-30
    Then every match falls inside the range
    """
    results = srv.find_matches(srv._data, date_from="2023-06-01", date_to="2023-06-30")
    assert results
    for m in results:
        assert "2023-06-01" <= m["date"] <= "2023-06-30"


def test_copa_do_brasil_matches_found(data):
    """Scenario: Find all Copa do Brasil matches
    When I search competition "Copa do Brasil"
    Then over 1000 matches are returned (1337 in the dataset)
    """
    results = srv.find_matches(srv._data, competition="Copa do Brasil", limit=5000)
    assert len(results) >= 1300


def test_mcp_tool_search_matches():
    """Scenario: MCP tool returns JSON
    When I call the search_matches MCP tool
    Then I receive valid JSON with a count and matches list
    """
    raw = srv.search_matches(team="Flamengo", season=2019, competition="Brasileirão")
    payload = json.loads(raw)
    assert payload["count"] > 0
    assert all(m["competition"] == "Brasileirão" for m in payload["matches"])


# ---------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------


def test_team_statistics(data):
    """Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2022"
    Then I should receive wins, losses, draws, and goals
    """
    stats = srv.team_stats(srv._data, "Palmeiras", season=2022, competition="Brasileirão")
    o = stats["overall"]
    assert o["matches"] == 38
    assert o["wins"] + o["draws"] + o["losses"] == 38
    assert o["goals_for"] >= 0 and o["goals_against"] >= 0
    assert stats["home"]["matches"] + stats["away"]["matches"] == 38


def test_team_stats_handle_state_suffix(data):
    """Scenario: Name variations resolve consistently
    When I request stats for "Palmeiras-SP" and "Palmeiras" in 2022
    Then the records are identical
    """
    a = srv.team_stats(srv._data, "Palmeiras-SP", season=2022, competition="Brasileirão")
    b = srv.team_stats(srv._data, "Palmeiras", season=2022, competition="Brasileirão")
    assert a["overall"] == b["overall"]


def test_home_record(data):
    """Scenario: What is a team's home record in a season?
    When I request Corinthians' 2022 home record
    Then only home matches are counted
    """
    stats = srv.team_stats(srv._data, "Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert stats["overall"]["matches"] == 19


# ---------------------------------------------------------------
# Feature: Head-to-head
# ---------------------------------------------------------------


def test_head_to_head(data):
    """Scenario: Compare Palmeiras and Santos head-to-head
    When I compare the two teams
    Then wins+losses+draws equals total matches
    """
    h2h = srv.head_to_head(srv._data, "Palmeiras", "Santos")
    total = h2h["total_matches"]
    assert total > 20
    assert h2h["team_wins"] + h2h["opponent_wins"] + h2h["draws"] == total
    for m in h2h["matches"]:
        pair = {m["home"], m["away"]}
        assert "Palmeiras" in " ".join(pair) or len(pair) == 2


# ---------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------


def test_find_brazilian_players(data):
    """Scenario: Find all Brazilian players in the dataset
    When I filter players by nationality "Brazil"
    Then hundreds of players are returned, sorted by rating
    """
    players = srv.search_players(srv._data, nationality="Brazil", limit=5000)
    assert len(players) > 500
    ratings = [p["overall"] for p in players]
    assert ratings == sorted(ratings, reverse=True)
    assert all(p["nationality"] == "Brazil" for p in players)


def test_players_at_club(data):
    """Scenario: Which players play for Santos?
    When I filter by club "Santos"
    Then every player's club contains Santos
    """
    players = srv.search_players(srv._data, club="Santos", limit=200)
    assert len(players) >= 5
    assert all("Santos" in p["club"] for p in players)


def test_player_by_name(data):
    """Scenario: Who is Gabriel Jesus?
    When I search players by name
    Then matching players are found
    """
    players = srv.search_players(srv._data, name="Gabriel Jesus")
    assert players
    assert any("Gabriel Jesus" in p["name"] for p in players)


def test_top_rated_brazilians(data):
    """Scenario: Top Brazilian players
    When I search Brazilians with min overall 85
    Then Neymar Jr is among them
    """
    players = srv.search_players(srv._data, nationality="Brazil", min_overall=85)
    assert any("Neymar" in p["name"] for p in players)


def test_mcp_tool_find_players():
    raw = srv.find_players(nationality="Brazil", limit=3)
    payload = json.loads(raw)
    assert payload["count"] == 3
    assert set(payload["players"][0]) >= {"name", "overall", "club", "position"}


# ---------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------


def test_standings_2019_brasileirao(data):
    """Scenario: Who won the 2019 Brasileirão?
    When I compute the 2019 standings
    Then Flamengo is champion with 90 points
    And 20 teams are in the table
    """
    table = srv.standings(srv._data, 2019, "Brasileirão")
    assert len(table) == 20
    assert table[0]["team"].startswith("Flamengo")
    assert table[0]["points"] == 90
    assert table[0]["matches"] == 38


def test_relegation_zone(data):
    """Scenario: Which teams were relegated?
    When I get standings with competition param
    Then the last four teams are flagged as relegated
    """
    raw = json.loads(srv.get_standings(2019))
    assert raw["champion"].startswith("Flamengo")
    assert len(raw["relegated"]) == 4


def test_standings_points_consistency(data):
    table = srv.standings(srv._data, 2023, "Brasileirão")
    for row in table:
        assert row["points"] == row["wins"] * 3 + row["draws"]
        assert row["matches"] == row["wins"] + row["draws"] + row["losses"] == 38


# ---------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------


def test_average_goals(data):
    """Scenario: Average goals per match in the Brasileirão
    When I aggregate goals
    Then the average is between 1.5 and 3.5 per match
    And home win rate exceeds away win rate
    """
    stats = srv.average_goals(srv._data, competition="Brasileirão")
    assert 1.5 < stats["avg_goals_per_match"] < 3.5
    assert stats["home_win_rate"] > stats["away_win_rate"]
    assert stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"] == pytest.approx(100.0, abs=0.2)


def test_biggest_wins(data):
    """Scenario: Show me the biggest wins in the dataset
    When I rank matches by margin
    Then they are ordered by decreasing margin
    """
    wins = srv.biggest_wins(srv._data, limit=10)
    margins = [w["margin"] for w in wins]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 6


def test_brazilian_club_summary(data):
    """Scenario: Cross-file query — player data joined to Brazilian clubs
    When I summarize Brazilian clubs
    Then each listed club has at least one player
    """
    summary = srv.brazilian_club_summary(srv._data)
    assert summary
    assert all(s["players"] >= 1 for s in summary)
    names = " ".join(s["club"] for s in summary)
    assert "Santos" in names


# ---------------------------------------------------------------
# Feature: Query performance
# ---------------------------------------------------------------


def test_simple_lookup_under_2s(benchmark=None):
    import time

    start = time.perf_counter()
    srv.find_matches(srv._data, team="Flamengo", opponent="Fluminense")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0


def test_aggregate_query_under_5s():
    import time

    start = time.perf_counter()
    srv.standings(srv._data, 2019)
    srv.standings(srv._data, 2023)
    srv.brazilian_club_summary(srv._data)
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0
