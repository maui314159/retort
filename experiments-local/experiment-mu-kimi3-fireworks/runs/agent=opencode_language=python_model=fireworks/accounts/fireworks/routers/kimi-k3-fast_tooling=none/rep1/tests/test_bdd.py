"""BDD step definitions for the feature files in tests/features/.

Implements the spec's Testing Approach: Gherkin scenarios over the
query engine (see TASK.md "Testing Approach").
"""

from __future__ import annotations

import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios(
    "features/matches.feature",
    "features/teams.feature",
    "features/players.feature",
    "features/competitions.feature",
    "features/statistics.feature",
)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("the match data is loaded")
def match_data_loaded(engine, context):
    context["engine"] = engine
    assert len(engine.matches) > 15000


@given("the player data is loaded")
def player_data_loaded(engine, context):
    context["engine"] = engine
    assert len(engine.players) == 18207


# ---------------------------------------------------------------------------
# When — match queries
# ---------------------------------------------------------------------------


@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_between(engine, context, team1, team2):
    context["result"] = engine.find_matches(team=team1, versus=team2)


@when(parsers.parse('I search for matches of "{team}" in season "{season}"'))
def search_team_season(engine, context, team, season):
    context["result"] = engine.find_matches(team=team, season=int(season))


@when(parsers.parse('I search for "{competition}" matches in season "{season}"'))
def search_competition_season(engine, context, competition, season):
    context["result"] = engine.find_matches(competition=competition, season=int(season))


@when(parsers.parse('I search for matches from "{date_from}" to "{date_to}"'))
def search_date_range(engine, context, date_from, date_to):
    context["result"] = engine.find_matches(
        date_from=date_from, date_to=date_to, limit=500
    )


@when(parsers.parse('I compare match counts for "{name_a}" and "{name_b}"'))
def compare_name_variations(engine, context, name_a, name_b):
    context["count_a"] = engine.find_matches(team=name_a)["total"]
    context["count_b"] = engine.find_matches(team=name_b)["total"]


@when(parsers.parse('I search for matches of "{team}"'))
def search_team(engine, context, team):
    context["result"] = engine.find_matches(team=team)


# ---------------------------------------------------------------------------
# When — team queries
# ---------------------------------------------------------------------------


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def team_statistics(engine, context, team, season):
    context["result"] = engine.team_record(team, season=int(season))


@when(parsers.parse('I request the home record of "{team}" in season "{season}" in "{competition}"'))
def team_home_record(engine, context, team, season, competition):
    context["result"] = engine.team_record(
        team, season=int(season), competition=competition, venue="home"
    )


@when(parsers.parse('I compare "{team1}" and "{team2}" head-to-head'))
def compare_head_to_head(engine, context, team1, team2):
    context["result"] = engine.head_to_head(team1, team2)


@when(parsers.parse('I ask which competitions "{team}" played'))
def which_competitions(engine, context, team):
    context["result"] = engine.team_competitions(team)


# ---------------------------------------------------------------------------
# When — player queries
# ---------------------------------------------------------------------------


@when(parsers.parse('I search for players with nationality "{nationality}"'))
def players_by_nationality(engine, context, nationality):
    context["result"] = engine.search_players(nationality=nationality, limit=10)


@when(parsers.parse('I search for players at club "{club}"'))
def players_by_club(engine, context, club):
    context["result"] = engine.search_players(club=club, limit=50)


@when(parsers.parse('I search for forwards at club "{club}"'))
def forwards_by_club(engine, context, club):
    context["result"] = engine.search_players(club=club, position_group="forward", limit=50)


@when(parsers.parse('I ask who "{name}" is'))
def who_is(engine, context, name):
    context["result"] = engine.player_profile(name)


# ---------------------------------------------------------------------------
# When — competition & statistics queries
# ---------------------------------------------------------------------------


@when(parsers.parse('I request the {season:d} "{competition}" standings'))
def standings(engine, context, season, competition):
    context["result"] = engine.standings(season, competition)


@when(parsers.parse('I request the {season:d} "{competition}" bracket'))
def bracket(engine, context, season, competition):
    context["result"] = engine.competition_schedule(competition, season=season, limit=500)


@when(parsers.parse('I request the {limit:d} biggest victories'))
def biggest_victories(engine, context, limit):
    context["result"] = engine.biggest_wins(limit=limit)


@when(parsers.parse('I request statistics for "{competition}"'))
def competition_statistics(engine, context, competition):
    context["result"] = engine.competition_stats(competition=competition)


@when(parsers.parse('I compare seasons {season_a:d} and {season_b:d} in "{competition}"'))
def compare_two_seasons(engine, context, season_a, season_b, competition):
    context["result"] = engine.compare_seasons(season_a, season_b, competition=competition)


@when(parsers.parse('I request the top scoring teams of {season:d} in "{competition}"'))
def top_scoring(engine, context, season, competition):
    context["result"] = engine.top_scoring_teams(season=season, competition=competition)


# ---------------------------------------------------------------------------
# Then — shared match assertions
# ---------------------------------------------------------------------------


@then("I should receive a list of matches")
def receive_matches(context):
    assert context["result"]["matches"], "expected a non-empty match list"


@then("each match should have date, scores, and competition")
def matches_have_fields(context):
    for m in context["result"]["matches"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", m["date"]), m["date"]
        assert isinstance(m["home_goals"], int)
        assert isinstance(m["away_goals"], int)
        assert m["competition"]


@then(parsers.parse("every match should be from season {season:d}"))
def matches_from_season(context, season):
    assert all(m["season"] == season for m in context["result"]["matches"])


@then(parsers.parse('every match should involve "{team}"'))
def matches_involve_team(context, team):
    for m in context["result"]["matches"]:
        assert team.lower() in (m["home_team"] + m["away_team"]).lower()


@then(parsers.parse('every match should be from competition "{competition}"'))
def matches_from_competition(context, competition):
    assert all(m["competition"] == competition for m in context["result"]["matches"])


@then(parsers.parse('every match date should be in "{month}"'))
def matches_in_month(context, month):
    assert all(m["date"].startswith(month) for m in context["result"]["matches"])


@then("both counts should be equal and positive")
def counts_equal(context):
    assert context["count_a"] == context["count_b"] > 0


@then("I should receive an unknown team error")
def unknown_team_error(context):
    assert "error" in context["result"]
    assert "Unknown team" in context["result"]["error"]


# ---------------------------------------------------------------------------
# Then — team assertions
# ---------------------------------------------------------------------------


@then("I should receive wins, losses, draws, and goals")
def receive_record(context):
    r = context["result"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in r and r[key] >= 0, key
    assert r["matches"] == r["wins"] + r["losses"] + r["draws"]


@then(parsers.parse("the record should show {matches:d} matches"))
def record_match_count(context, matches):
    assert context["result"]["matches"] == matches


@then("the record should include a win rate")
def record_win_rate(context):
    assert 0 <= context["result"]["win_rate_pct"] <= 100


@then("I should see wins for both sides and draws")
def h2h_both_sides(context):
    r = context["result"]
    assert r["team1_wins"] > 0 and r["team2_wins"] > 0 and r["draws"] > 0


@then("the most recent match should be included")
def h2h_last_match(context):
    assert context["result"]["last_match"] is not None


@then(parsers.parse('the answer should include "{competition}"'))
def answer_includes_competition(context, competition):
    comps = {c["competition"] for c in context["result"]["competitions"]}
    assert competition in comps, f"{competition} not in {comps}"


# ---------------------------------------------------------------------------
# Then — player assertions
# ---------------------------------------------------------------------------


@then(parsers.parse("I should receive more than {count:d} players"))
def receive_many_players(context, count):
    assert context["result"]["total"] > count


@then(parsers.parse('the top player should be "{name}"'))
def top_player(context, name):
    assert context["result"]["players"][0]["name"] == name


@then(parsers.parse('every player should have club "{club}"'))
def players_club(context, club):
    assert context["result"]["players"]
    assert all(p["club"] == club for p in context["result"]["players"])


@then("every player should be a forward")
def players_forwards(context):
    assert context["result"]["players"]
    assert all(p["position_group"] == "forward" for p in context["result"]["players"])


@then(parsers.parse("the profile should show overall rating {overall:d}"))
def profile_overall(context, overall):
    assert context["result"]["overall"] == overall


@then(parsers.parse('the profile should show club "{club}"'))
def profile_club(context, club):
    assert context["result"]["club"] == club


@then("I should receive a not found message")
def not_found_message(context):
    assert "error" in context["result"]


# ---------------------------------------------------------------------------
# Then — competition & statistics assertions
# ---------------------------------------------------------------------------


@then(parsers.parse('the champion should be "{team}" with {points:d} points'))
def champion_with_points(context, team, points):
    r = context["result"]
    assert r["champion"] == team
    assert r["standings"][0]["points"] == points


@then(parsers.parse("the table should have {count:d} teams"))
def table_size(context, count):
    assert len(context["result"]["standings"]) == count


@then(parsers.parse("every team should have played {played:d} matches"))
def teams_played(context, played):
    assert all(r["played"] == played for r in context["result"]["standings"])


@then("points should equal 3 per win plus 1 per draw")
def points_math(context):
    for r in context["result"]["standings"]:
        assert r["points"] == 3 * r["wins"] + r["draws"]


@then(parsers.parse("{count:d} teams should be marked as relegated"))
def relegated_count(context, count):
    assert len(context["result"]["relegated"]) == count


@then(parsers.parse('the stages should include "{stage}"'))
def stages_include(context, stage):
    assert stage in context["result"]["stages"]


@then("the margins should be sorted descending")
def margins_sorted(context):
    wins = context["result"]["biggest_wins"]
    margins = [abs(m["home_goals"] - m["away_goals"]) for m in wins]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the biggest margin should be at least {margin:d} goals"))
def biggest_margin(context, margin):
    m = context["result"]["biggest_wins"][0]
    assert abs(m["home_goals"] - m["away_goals"]) >= margin


@then(parsers.parse("the average goals per match should be between {lo:g} and {hi:g}"))
def avg_goals_between(context, lo, hi):
    avg = context["result"]["avg_goals_per_match"]
    assert lo < avg < hi


@then("the home win rate should exceed the away win rate")
def home_advantage(context):
    r = context["result"]
    assert r["home_win_rate_pct"] > r["away_win_rate_pct"]


@then(parsers.parse("both seasons should have {matches:d} matches"))
def both_seasons_matches(context, matches):
    assert context["result"]["season_a"]["matches"] == matches
    assert context["result"]["season_b"]["matches"] == matches


@then(parsers.parse('the first team should be "{team}"'))
def first_team(context, team):
    assert context["result"]["top_scoring_teams"][0]["team"] == team
