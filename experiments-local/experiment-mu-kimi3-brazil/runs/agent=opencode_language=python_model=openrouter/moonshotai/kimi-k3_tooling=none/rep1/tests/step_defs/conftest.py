"""Shared BDD step definitions for the Brazilian soccer MCP features."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, then, when

from brazilian_soccer_mcp import queries as q


@pytest.fixture
def ctx() -> dict:
    """Scenario-local bag for When/Then handoff."""
    return {}


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given("the match data is loaded")
def match_data_loaded(kb, ctx):
    ctx["kb"] = kb
    assert len(kb.matches) > 0


@given("the player data is loaded")
def player_data_loaded(kb, ctx):
    ctx["kb"] = kb
    assert len(kb.players) > 0


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_between(kb, ctx, team_a, team_b):
    ctx["result"] = q.find_matches(kb, team=team_a, opponent=team_b, limit=100)


@when(parsers.parse('I search for matches of "{team}" in season "{season}"'))
def search_team_season(kb, ctx, team, season):
    ctx["result"] = q.find_matches(kb, team=team, season=int(season), limit=100)


@when(parsers.parse('I search for "{competition}" matches of "{team}"'))
def search_team_competition(kb, ctx, competition, team):
    ctx["result"] = q.find_matches(kb, team=team, competition=competition, limit=100)


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def request_stats(kb, ctx, team, season):
    ctx["result"] = q.team_stats(team, kb, season=int(season))


@when(parsers.parse('I request the home record of "{team}" in season "{season}"'))
def request_home_record(kb, ctx, team, season):
    ctx["result"] = q.team_stats(team, kb, season=int(season), venue="home",
                                 competition="Brasileirão")


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def request_h2h(kb, ctx, team_a, team_b):
    ctx["result"] = q.head_to_head(team_a, team_b, kb)


@when(parsers.parse('I request the "{season}" "{competition}" standings'))
def request_standings(kb, ctx, season, competition):
    ctx["result"] = q.standings(int(season), kb, competition=competition)


@when("I list the competitions")
def request_competitions(kb, ctx):
    ctx["result"] = q.list_competitions(kb)


@when(parsers.parse('I search for players named "{name}"'))
def search_player_name(kb, ctx, name):
    ctx["result"] = q.search_players(kb, name=name)


@when("I search for Brazilian players")
def search_brazilians(kb, ctx):
    ctx["result"] = q.search_players(kb, nationality="Brazil", limit=25)


@when(parsers.parse('I search for players of club "{club}"'))
def search_club(kb, ctx, club):
    ctx["result"] = q.search_players(kb, club=club, limit=50)


@when(parsers.parse("I search for the top {n:d} Brazilian players"))
def search_top_brazilians(kb, ctx, n):
    ctx["result"] = q.search_players(kb, nationality="Brazil", limit=n)


@when(parsers.parse('I compute statistics for "{competition}" in season "{season}"'))
def compute_stats(kb, ctx, competition, season):
    ctx["result"] = q.competition_stats(kb, competition=competition, season=int(season))


@when(parsers.parse('I compute statistics for "{competition}" in seasons "{s1}" and "{s2}"'))
def compute_stats_two_seasons(kb, ctx, competition, s1, s2):
    ctx["result"] = [
        q.competition_stats(kb, competition=competition, season=int(s1)),
        q.competition_stats(kb, competition=competition, season=int(s2)),
    ]


@when(parsers.parse("I request the {n:d} biggest wins"))
def request_biggest(kb, ctx, n):
    ctx["result"] = q.biggest_wins(kb, limit=n)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then("I should receive a list of matches")
def check_match_list(ctx):
    assert ctx["result"]["total"] > 0
    assert ctx["result"]["matches"]


@then("each match should have date, scores, and competition")
def check_match_fields(ctx):
    for match in ctx["result"]["matches"]:
        assert match["date"]
        assert match["home_goals"] is not None
        assert match["away_goals"] is not None
        assert match["competition"]


@then(parsers.parse('every match should be between "{team_a}" and "{team_b}"'))
def check_both_teams(ctx, team_a, team_b):
    for match in ctx["result"]["matches"]:
        assert {match["home_team"], match["away_team"]} == {team_a, team_b}


@then(parsers.parse('every match should involve "{team}"'))
def check_involves(ctx, team):
    for match in ctx["result"]["matches"]:
        assert team in (match["home_team"], match["away_team"])


@then(parsers.parse("every match should be from season {season:d}"))
def check_season(ctx, season):
    assert ctx["result"]["total"] > 0
    for match in ctx["result"]["matches"]:
        assert match["season"] == season


@then(parsers.parse('every match should be in competition "{competition}"'))
def check_competition(ctx, competition):
    assert ctx["result"]["total"] > 0
    for match in ctx["result"]["matches"]:
        assert match["competition"] == competition


@then("I should receive wins, losses, draws, and goals")
def check_record(ctx):
    result = ctx["result"]
    assert result["matches"] > 0
    assert result["wins"] + result["draws"] + result["losses"] == result["matches"]
    assert result["goals_for"] >= 0
    assert result["goals_against"] >= 0


@then("the win rate should be reported")
def check_win_rate(ctx):
    assert 0.0 <= ctx["result"]["win_rate"] <= 100.0


@then(parsers.parse("the team should have played {n:d} matches"))
def check_played(ctx, n):
    assert ctx["result"]["matches"] == n


@then("the summary should include wins for both teams and draws")
def check_h2h_summary(ctx):
    result = ctx["result"]
    assert result["total"] > 0
    assert result["wins_a"] >= 0 and result["wins_b"] >= 0 and result["draws"] >= 0
    assert result["wins_a"] + result["wins_b"] + result["draws"] == result["total"]


@then(parsers.parse('the listed matches should involve "{team_a}" and "{team_b}"'))
def check_h2h_matches(ctx, team_a, team_b):
    for match in ctx["result"]["matches"]:
        assert {match["home_team"], match["away_team"]} == {team_a, team_b}


@then(parsers.parse("the table should contain {n:d} teams"))
def check_table_size(ctx, n):
    assert len(ctx["result"]["table"]) == n


@then(parsers.parse('"{team}" should be the champion'))
def check_champion(ctx, team):
    table = ctx["result"]["table"]
    assert table[0]["team"] == team
    assert table[0]["champion"] is True


@then(parsers.parse("{n:d} teams should be marked as relegated"))
def check_relegation_count(ctx, n):
    relegated = [row for row in ctx["result"]["table"] if row["relegated"]]
    assert len(relegated) == n


@then(parsers.parse('"{team}" should be relegated'))
def check_team_relegated(ctx, team):
    relegated = {row["team"] for row in ctx["result"]["table"] if row["relegated"]}
    assert team in relegated


@then(parsers.parse('the list should include "{competition}"'))
def check_includes_competition(ctx, competition):
    names = {c["competition"] for c in ctx["result"]["competitions"]}
    assert competition in names


@then("I should receive a list of players")
def check_player_list(ctx):
    assert ctx["result"]["total"] > 0
    assert ctx["result"]["players"]


@then(parsers.parse('the top player should be "{name}"'))
def check_top_player(ctx, name):
    assert ctx["result"]["players"][0]["name"] == name


@then("each player should have name, rating, position, and club")
def check_player_fields(ctx):
    for player in ctx["result"]["players"]:
        assert player["name"]
        assert player["overall"] is not None
        assert player["position"]
        assert player["club"]


@then("all returned players should be Brazilian")
def check_all_brazilian(ctx):
    assert ctx["result"]["players"]
    for player in ctx["result"]["players"]:
        assert player["nationality"] == "Brazil"


@then(parsers.parse('every player should belong to club "{club}"'))
def check_player_club(ctx, club):
    assert ctx["result"]["players"]
    for player in ctx["result"]["players"]:
        assert club in player["club"]


@then("players should be ordered by overall rating")
def check_rating_order(ctx):
    ratings = [p["overall"] for p in ctx["result"]["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then("the average goals per match should be reported")
def check_avg_goals(ctx):
    assert ctx["result"]["avg_goals_per_match"] > 0


@then("the home win rate should be reported")
def check_home_rate(ctx):
    assert 0.0 < ctx["result"]["home_win_rate"] < 100.0


@then("each entry should show winner, loser, score, and competition")
def check_biggest_fields(ctx):
    assert ctx["result"]["biggest_wins"]
    for win in ctx["result"]["biggest_wins"]:
        assert win["winner"] and win["loser"]
        assert "-" in win["score"]
        assert win["competition"]


@then("the winning margins should be in descending order")
def check_margin_order(ctx):
    margins = [w["margin"] for w in ctx["result"]["biggest_wins"]]
    assert margins == sorted(margins, reverse=True)


@then("both seasons should report average goals per match")
def check_both_seasons(ctx):
    assert len(ctx["result"]) == 2
    for stats in ctx["result"]:
        assert stats["avg_goals_per_match"] > 0
