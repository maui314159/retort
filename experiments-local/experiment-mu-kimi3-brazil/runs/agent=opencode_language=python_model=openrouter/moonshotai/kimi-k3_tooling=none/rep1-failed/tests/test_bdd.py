"""pytest-bdd step definitions for the specification's BDD scenarios."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data import get_dataset

scenarios(
    "features/match_queries.feature",
    "features/team_queries.feature",
    "features/player_queries.feature",
    "features/competition_queries.feature",
    "features/statistics.feature",
)


@pytest.fixture
def ctx():
    """Shared context between Given/When/Then steps of a scenario."""
    return {}


# ----------------------------------------------------------------------
# Given
# ----------------------------------------------------------------------


@given("the match data is loaded")
def match_data_loaded(ctx):
    ctx["ds"] = get_dataset()
    assert len(ctx["ds"].matches) > 0


@given("the player data is loaded")
def player_data_loaded(ctx):
    ctx["ds"] = get_dataset()
    assert len(ctx["ds"].players) > 0


# ----------------------------------------------------------------------
# When — match queries
# ----------------------------------------------------------------------


@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_between(ctx, team_a, team_b):
    ctx["result"] = queries.find_matches(team=team_a, opponent=team_b, dataset=ctx["ds"])


@when(parsers.parse('I search for matches of "{team}" in season {season:d}'))
def search_team_season(ctx, team, season):
    ctx["result"] = queries.find_matches(team=team, season=season, dataset=ctx["ds"])


@when(parsers.parse('I search for "{competition}" finals'))
def search_finals(ctx, competition):
    ctx["result"] = queries.find_matches(
        competition=competition, stage="final", dataset=ctx["ds"]
    )


@when(parsers.parse('I search for "{team}" matches between "{start}" and "{end}"'))
def search_date_range(ctx, team, start, end):
    ctx["result"] = queries.find_matches(
        team=team, date_from=start, date_to=end, dataset=ctx["ds"]
    )


@when(parsers.parse('I search for matches of "{name_a}" and of "{name_b}" in season {season:d}'))
def search_name_variants(ctx, name_a, name_b, season):
    ctx["result_a"] = queries.find_matches(team=name_a, season=season, dataset=ctx["ds"])
    ctx["result_b"] = queries.find_matches(team=name_b, season=season, dataset=ctx["ds"])


# ----------------------------------------------------------------------
# When — team queries
# ----------------------------------------------------------------------


@when(parsers.parse('I request statistics for "{team}" in season "{season:d}"'))
def request_stats(ctx, team, season):
    ctx["result"] = queries.team_statistics(team, season=season, dataset=ctx["ds"])


@when(parsers.parse('I request the home record of "{team}" in season "{season:d}"'))
def request_home_record(ctx, team, season):
    ctx["result"] = queries.team_statistics(
        team, season=season, venue="home", competition="Brasileirão", dataset=ctx["ds"]
    )


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def compare_h2h(ctx, team_a, team_b):
    ctx["result"] = queries.head_to_head(team_a, team_b, dataset=ctx["ds"])


@when(parsers.parse('I ask which competitions "{team}" played in'))
def ask_team_competitions(ctx, team):
    ctx["result"] = queries.team_competitions(team, dataset=ctx["ds"])


# ----------------------------------------------------------------------
# When — player queries
# ----------------------------------------------------------------------


@when(parsers.parse('I search for a player named "{name}"'))
def search_player(ctx, name):
    ctx["result"] = queries.search_players(name=name, dataset=ctx["ds"])


@when(parsers.parse('I filter players by nationality "{nationality}"'))
def filter_nationality(ctx, nationality):
    ctx["result"] = queries.search_players(nationality=nationality, dataset=ctx["ds"])


@when(parsers.parse('I filter players by club "{club}"'))
def filter_club(ctx, club):
    ctx["result"] = queries.search_players(club=club, dataset=ctx["ds"])


@when(parsers.parse('I filter players by club "{club}" and position "{position}"'))
def filter_club_position(ctx, club, position):
    ctx["result"] = queries.search_players(club=club, position=position, dataset=ctx["ds"])


@when(parsers.parse("I ask for the top {limit:d} Brazilian players"))
def top_brazilian(ctx, limit):
    ctx["result"] = queries.top_players(nationality="Brazil", limit=limit, dataset=ctx["ds"])


# ----------------------------------------------------------------------
# When — competition queries
# ----------------------------------------------------------------------


@when(parsers.parse("I request the standings for season {season:d}"))
def request_standings(ctx, season):
    ctx["result"] = queries.standings(season, dataset=ctx["ds"])


@when("I list the competitions")
def list_comps(ctx):
    ctx["result"] = queries.list_competitions(dataset=ctx["ds"])


@when(parsers.parse('I list the teams of "{competition}" season {season:d}'))
def list_season_teams(ctx, competition, season):
    ctx["result"] = queries.list_teams(competition=competition, season=season, dataset=ctx["ds"])


# ----------------------------------------------------------------------
# When — statistics
# ----------------------------------------------------------------------


@when(parsers.parse("I ask for the {limit:d} biggest wins"))
def ask_biggest_wins(ctx, limit):
    ctx["result"] = queries.biggest_wins(limit=limit, dataset=ctx["ds"])


@when(parsers.parse('I ask for the overview of "{competition}" season {season:d}'))
def ask_overview(ctx, competition, season):
    ctx["result"] = queries.competition_overview(
        competition=competition, season=season, dataset=ctx["ds"]
    )


@when("I count Brazilian players per club")
def count_players_per_club(ctx):
    ctx["result"] = queries.players_by_club(nationality="Brazil", dataset=ctx["ds"])


# ----------------------------------------------------------------------
# Then — shared match assertions
# ----------------------------------------------------------------------


@then("I should receive a list of matches")
def check_match_list(ctx):
    assert ctx["result"]["count"] > 0
    assert len(ctx["result"]["matches"]) > 0


@then("each match should have date, scores, and competition")
def check_match_fields(ctx):
    for m in ctx["result"]["matches"]:
        assert m["date"]
        assert m["home_goals"] is not None and m["away_goals"] is not None
        assert m["competition"]


@then(parsers.parse('every match should involve "{team}"'))
def check_involves(ctx, team):
    for m in ctx["result"]["matches"]:
        assert team in (m["home_team"], m["away_team"])


@then(parsers.parse("every match should be from season {season:d}"))
def check_season(ctx, season):
    assert all(m["season"] == season for m in ctx["result"]["matches"])


@then(parsers.parse('each match should be from "{competition}"'))
def check_competition(ctx, competition):
    assert all(m["competition"] == competition for m in ctx["result"]["matches"])


@then(parsers.parse('every match should have stage "{stage}"'))
def check_stage(ctx, stage):
    assert all(m["stage"] == stage for m in ctx["result"]["matches"])


@then(parsers.parse('every match date should start with "{prefix}"'))
def check_date_prefix(ctx, prefix):
    assert all(m["date"].startswith(prefix) for m in ctx["result"]["matches"])


@then("both searches should return the same number of matches")
def check_same_count(ctx):
    assert ctx["result_a"]["count"] == ctx["result_b"]["count"] > 0


# ----------------------------------------------------------------------
# Then — team assertions
# ----------------------------------------------------------------------


@then("I should receive wins, losses, draws, and goals")
def check_stats_fields(ctx):
    res = ctx["result"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert res[key] is not None
    assert res["matches"] == res["wins"] + res["losses"] + res["draws"]


@then(parsers.parse("the record should show {matches:d} matches"))
def check_record_matches(ctx, matches):
    assert ctx["result"]["matches"] == matches


@then("the wins, draws and losses should add up to the matches played")
def check_h2h_consistency(ctx):
    res = ctx["result"]
    total = res["team_a_wins"] + res["team_b_wins"] + res["draws"]
    assert total == res["matches_played"]


@then(parsers.parse('the answer should include "{c1}", "{c2}" and "{c3}"'))
def check_competitions_include(ctx, c1, c2, c3):
    names = {c["competition"] for c in ctx["result"]["competitions"]}
    assert {c1, c2, c3} <= names


# ----------------------------------------------------------------------
# Then — player assertions
# ----------------------------------------------------------------------


@then(parsers.parse('the top result should be "{name}" with overall {overall:d}'))
def check_top_player(ctx, name, overall):
    top = ctx["result"]["players"][0]
    assert top["name"] == name
    assert top["overall"] == overall


@then(parsers.parse('every returned player should have nationality "{nationality}"'))
def check_nationality(ctx, nationality):
    assert ctx["result"]["count"] > 0
    assert all(p["nationality"] == nationality for p in ctx["result"]["players"])


@then(parsers.parse('every returned player should play for "{club}"'))
def check_club(ctx, club):
    assert ctx["result"]["count"] > 0
    assert all(p["club"] == club for p in ctx["result"]["players"])


@then("every returned player should be a forward")
def check_forwards(ctx):
    forwards = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
    assert ctx["result"]["count"] > 0
    assert all(p["position"] in forwards for p in ctx["result"]["players"])


@then(parsers.parse('the first player should be "{name}"'))
def check_first_player(ctx, name):
    assert ctx["result"]["players"][0]["name"] == name


@then("I should receive zero players")
def check_zero_players(ctx):
    assert ctx["result"]["count"] == 0
    assert ctx["result"]["players"] == []


# ----------------------------------------------------------------------
# Then — competition / statistics assertions
# ----------------------------------------------------------------------


@then(parsers.parse('the champion should be "{team}" with {points:d} points'))
def check_champion(ctx, team, points):
    assert ctx["result"]["champion"] == team
    assert ctx["result"]["table"][0]["points"] == points


@then("every row should satisfy points equals 3 per win plus 1 per draw")
def check_points_math(ctx):
    for row in ctx["result"]["table"]:
        assert row["points"] == 3 * row["wins"] + row["draws"]


@then(parsers.parse('the list should include "{c1}", "{c2}" and "{c3}"'))
def check_comp_list(ctx, c1, c2, c3):
    names = {c["competition"] for c in ctx["result"]["competitions"]}
    assert {c1, c2, c3} <= names


@then(parsers.parse("there should be {count:d} teams"))
def check_team_count(ctx, count):
    assert ctx["result"]["count"] == count


@then("the margins should be in non-increasing order")
def check_margins(ctx):
    margins = [r["margin"] for r in ctx["result"]["results"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the average goals per match should be between {lo:f} and {hi:f}"))
def check_avg_goals(ctx, lo, hi):
    assert lo < ctx["result"]["avg_goals_per_match"] < hi


@then("home wins should be more frequent than away wins")
def check_home_advantage(ctx):
    assert ctx["result"]["home_win_pct"] > ctx["result"]["away_win_pct"]


@then("at least one Brazilian club should appear")
def check_brazilian_club_appears(ctx):
    known = {"Grêmio", "Santos", "Flamengo", "Palmeiras", "Botafogo", "Cruzeiro"}
    clubs = {c["club"] for c in ctx["result"]["clubs"]}
    assert clubs & known
