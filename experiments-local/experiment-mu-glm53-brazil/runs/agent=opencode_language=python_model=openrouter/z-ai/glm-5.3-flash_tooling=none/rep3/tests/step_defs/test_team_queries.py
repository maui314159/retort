"""BDD step definitions for the Team Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

scenarios("../features/team_queries.feature")


@given("the match data is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'), target_fixture="result")
def team_season_stats(store, team, season):
    return store.team_stats(team, season=int(season))


@when(parsers.parse(
    'I request the home record of "{team}" in the "{competition}" in season "{season}"'), target_fixture="result")
def team_home_stats(store, team, competition, season):
    return store.team_stats(team, season=int(season), competition=competition,
                            venue="home")


@when(parsers.parse('I request the head-to-head record of "{team_a}" and "{team_b}"'), target_fixture="result")
def team_h2h(store, team_a, team_b):
    return store.head_to_head(team_a, team_b)


@when(parsers.parse('I request the history of "{team}"'), target_fixture="result")
def team_history(store, team):
    return store.team_history(team)


@when(parsers.parse('I request statistics for "{team}"'), target_fixture="result")
def unknown_team_stats(store, team):
    try:
        return {"result": store.team_stats(team)}
    except LookupError as exc:
        return {"error": exc}


@then("I should receive wins, losses, draws, and goals")
def assert_record_fields(result):
    for field in ("matches", "wins", "draws", "losses",
                  "goals_for", "goals_against"):
        assert field in result, f"missing {field}"
    assert result["matches"] > 0


@then("the head-to-head should include wins, draws and goals for both teams")
def assert_h2h_fields(result):
    assert result["team_a_wins"] + result["team_b_wins"] + result["draws"] \
        == result["total_matches"]
    assert result["team_a_goals"] >= 0 and result["team_b_goals"] >= 0


@then("the win rate should be consistent with the record")
def assert_win_rate(result):
    total = result["wins"] + result["draws"] + result["losses"]
    assert total == result["matches"]
    expected = round(100.0 * result["wins"] / total, 1)
    assert result["win_rate"] == expected


@then("all matches should be home matches")
def assert_home_venue(result):
    assert result["venue"] == "home"
    assert 10 <= result["matches"] <= 30      # half a season plus cup slack


@then(parsers.parse('the competitions should include "{comp_a}", "{comp_b}" and "{comp_c}"'))
def assert_history_competitions(result, comp_a, comp_b, comp_c):
    comps = result["competitions"]
    assert comp_a in comps and comp_b in comps and comp_c in comps


@then("a not-found error should be raised")
def assert_not_found(result):
    assert isinstance(result, dict) and "error" in result
