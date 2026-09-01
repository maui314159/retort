"""BDD step definitions for the Statistical Analysis feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

scenarios("../features/statistics.feature")


@given("the match data is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I request statistics for "{competition}"'), target_fixture="result")
def request_stats(store, competition):
    return store.statistics(competition=competition)


@when(parsers.parse('I request the biggest wins for "{competition}"'), target_fixture="result")
def request_biggest_wins(store, competition):
    return store.statistics(competition=competition)


@when(parsers.parse("I request derbies for season {season:d}"), target_fixture="result")
def request_derbies(store, season):
    return store.derbies(season=season)


@then("the average goals per match should be plausible")
def assert_avg_goals(result):
    assert 2.0 <= result["avg_goals_per_match"] <= 3.5
    assert result["matches"] > 1000


@then("the home win rate should be plausible")
def assert_home_rate(result):
    assert 30.0 <= result["home_win_rate"] <= 60.0
    assert result["home_wins"] + result["away_wins"] + result["draws"] \
        == result["matches"]


@then("I should receive a descending list of victories")
def assert_wins_desc(result):
    wins = result["biggest_wins"]
    assert len(wins) == 10
    margins = []
    for w in wins:
        gf, ga = (int(x) for x in w["score"].split("-"))
        margins.append(abs(gf - ga))
    assert margins == sorted(margins, reverse=True)


@then("the top victory should have a margin of at least 5 goals")
def assert_top_margin(result):
    gf, ga = (int(x) for x in result["biggest_wins"][0]["score"].split("-"))
    assert abs(gf - ga) >= 5


@then("I should receive traditional rivalries with records")
def assert_derby_records(result):
    assert result["derbies"]
    for d in result["derbies"]:
        assert d["total_matches"] > 0
        assert d["team_a_wins"] + d["team_b_wins"] + d["draws"] == d["total_matches"]


@then(parsers.parse('the list should include "{derby_a}" and "{derby_b}"'))
def assert_derby_names(result, derby_a, derby_b):
    names = {d["derby"] for d in result["derbies"]}
    assert derby_a in names and derby_b in names


@then("the best away record should not exceed the best home record")
def assert_home_beats_away(result):
    best_home = result["best_home_records"][0]["win_rate"]
    best_away = result["best_away_records"][0]["win_rate"]
    assert best_away <= best_home
