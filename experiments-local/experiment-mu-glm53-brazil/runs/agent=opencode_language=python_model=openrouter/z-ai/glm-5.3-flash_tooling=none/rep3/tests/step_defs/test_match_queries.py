"""BDD step definitions for the Match Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

scenarios("../features/match_queries.feature")


@given("the match data is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'), target_fixture="result")
def search_between(store, team_a, team_b):
    return store.head_to_head(team_a, team_b)


@when(parsers.parse('I request the head-to-head record of "{team_a}" and "{team_b}"'), target_fixture="result")
def request_h2h(store, team_a, team_b):
    return store.head_to_head(team_a, team_b)


@when(parsers.parse('I search for matches of "{team}" in season {season:d}'), target_fixture="result")
def search_team_season(store, team, season):
    return store.search_matches(team=team, season=season, limit=100)


@when(parsers.parse('I search for matches between dates "{start}" and "{end}"'), target_fixture="result")
def search_date_range(store, start, end):
    return store.search_matches(date_from=start, date_to=end, limit=100)


@when(parsers.parse('I search for stage "{stage}" in "{competition}"'), target_fixture="result")
def search_stage(store, stage, competition):
    return store.search_matches(stage=stage, competition=competition, limit=100)


@when(parsers.parse('I search for stage "{stage}" in "{competition}" for season {season:d}'), target_fixture="result")
def search_stage_season(store, stage, competition, season):
    return store.search_matches(stage=stage, competition=competition,
                                season=season, limit=100)


@then("I should receive a list of matches")
def assert_match_list(result):
    assert isinstance(result.get("matches"), list)
    assert result["total"] > 0
    assert result["matches"], "expected at least one match"


@then("each match should have date, scores, and competition")
def assert_match_fields(result):
    for m in result["matches"]:
        assert m["date"], f"missing date: {m}"
        assert m["home_goal"] is not None and m["away_goal"] is not None
        assert m["competition"], f"missing competition: {m}"


@then("the response should include a head-to-head summary")
def assert_h2h_summary(result):
    for field in ("team_a_wins", "team_b_wins", "draws",
                  "team_a_goals", "team_b_goals"):
        assert field in result


@then("the head-to-head should include wins, draws and goals for both teams")
def assert_h2h_fields(result):
    assert result["team_a_wins"] + result["team_b_wins"] + result["draws"] \
        == result["total_matches"]
    assert result["team_a_goals"] >= 0 and result["team_b_goals"] >= 0


@then(parsers.parse('the rivalry should be recognized as "{derby_name}"'))
def assert_derby(result, derby_name):
    assert result["derby"] == derby_name


@then(parsers.parse("every match should be in season {season:d}"))
def assert_season(result, season):
    assert result["matches"]
    for m in result["matches"]:
        assert m["season"] == season


@then("every match date should fall within the range")
def assert_date_range(result):
    assert result["matches"]
    for m in result["matches"]:
        assert "2019-05-01" <= m["date"] <= "2019-05-31"


@then("every match should be a cup final")
def assert_cup_final(result):
    assert result["matches"]
    for m in result["matches"]:
        assert m["stage"] == "final"
        assert m["competition"] == "Copa do Brasil"


@then(parsers.parse('the finalists should include "{team_a}" and "{team_b}"'))
def assert_finalists(result, team_a, team_b):
    names = {m["home"] for m in result["matches"]} | {m["away"] for m in result["matches"]}
    assert team_a in names and team_b in names
