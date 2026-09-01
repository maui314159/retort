"""BDD steps for the Statistical Analysis feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.service import SoccerDataService

scenarios("features/statistics_queries.feature")


@given("the match data is loaded", target_fixture="svc")
def given_match_data(service: SoccerDataService):
    return service


@when(parsers.parse('I request league statistics for "{competition}"'),
      target_fixture="result")
def when_league_statistics(svc, competition):
    return svc.league_statistics(competition=competition)


@when(parsers.parse("I request the {count} biggest wins"), target_fixture="result")
def when_biggest_wins(svc, count):
    return svc.biggest_wins(n=int(count))


@when(parsers.parse('I request the best home records in "{competition}"'),
      target_fixture="result")
def when_best_home(svc, competition):
    return svc.best_records(competition=competition, venue="home")


@when("I request the best away records", target_fixture="result")
def when_best_away(svc):
    return svc.best_records(venue="away")


@when(parsers.parse('I request league statistics for "{competition}" season {season}'),
      target_fixture="result")
def when_league_statistics_season(svc, competition, season):
    return svc.league_statistics(competition=competition, season=int(season))


@when("I request derby matches", target_fixture="result")
def when_derbies(svc):
    return svc.derbies()


@when(parsers.parse("I request derby matches for season {season}"),
      target_fixture="result")
def when_derbies_season(svc, season):
    return svc.derbies(season=int(season))


@then(parsers.parse("the average goals per match should be between {low} and {high}"))
def then_avg_goals(result, low, high):
    assert "error" not in result
    assert float(low) <= result["avg_goals_per_match"] <= float(high)


@then("the home win rate should be higher than the away win rate")
def then_home_advantage(result):
    assert result["home_win_rate"] > result["away_win_rate"]


@then("the largest margin should be at least 8 goals")
def then_largest_margin(result):
    assert result["wins"][0]["margin"] >= 8


@then("wins should be ordered by decreasing margin")
def then_margin_ordering(result):
    margins = [win["margin"] for win in result["wins"]]
    assert margins == sorted(margins, reverse=True), margins


@then("the records should be ranked by win rate")
def then_ranked_by_win_rate(result):
    records = result["records"]
    assert len(records) >= 5
    rates = [record["win_rate"] for record in records]
    assert rates == sorted(rates, reverse=True), rates


@then("the records should not be empty")
def then_records_not_empty(result):
    assert "error" not in result
    assert result["records"]


@then(parsers.parse('the {derby} derby should be listed'))
def then_derby_listed(result, derby):
    names = [entry["derby"] for entry in result["derbies"]]
    assert derby in names, names


@then("every derby should have a positive match count")
def then_derby_counts(result):
    for entry in result["derbies"]:
        assert entry["total_matches"] > 0
        assert entry["record"]["matches"] > 0


@then("the seasons should be comparable")
def then_seasons_comparable(result):
    assert "error" not in result
    assert result["matches"] > 0
    assert result["avg_goals_per_match"] > 0
