"""BDD step definitions for the Competition Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

scenarios("../features/competition_queries.feature")


@given("the match data is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I request the standings of "{competition}" for season {season:d}'), target_fixture="result")
def request_standings(store, competition, season):
    try:
        return {"result": store.standings(competition, season)}
    except LookupError as exc:
        return {"error": exc}


@when("I request the list of competitions", target_fixture="result")
def request_competitions(store):
    return store.competitions()


@when(parsers.parse('I compare seasons {season_a:d} and {season_b:d} of "{competition}"'), target_fixture="result")
def compare_seasons(store, season_a, season_b, competition):
    return store.compare_seasons(competition, season_a, season_b)


@then(parsers.parse('the champion should be "{team}"'))
def assert_champion(result, team):
    assert result["result"]["champion"] == team


@then("the table should cover 20 teams and 380 matches")
def assert_table_size(result):
    table = result["result"]["table"]
    assert len(table) == 20
    assert sum(r["matches"] for r in table) // 2 == 380
    assert result["result"]["total_matches_used"] == 380


@then("a relegation zone with 4 teams should be reported")
def assert_relegation(result):
    zone = result["result"].get("relegation_zone")
    assert isinstance(zone, list) and len(zone) == 4


@then("a not-found error should be raised")
def assert_not_found(result):
    assert isinstance(result, dict) and "error" in result


@then(parsers.parse('the catalog should include "{comp_a}", "{comp_b}" and "{comp_c}"'))
def assert_catalog(result, comp_a, comp_b, comp_c):
    names = {c["competition"] for c in result["competitions"]}
    assert {comp_a, comp_b, comp_c} <= names


@then("both seasons should report a champion and aggregates")
def assert_comparison(result):
    assert result["champions"][2018] and result["champions"][2019]
    for row in result["seasons"]:
        assert row["matches"] > 0
        assert row["avg_goals_per_match"] > 0
