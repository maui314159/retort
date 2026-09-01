"""BDD steps for the Match Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.service import SoccerDataService

scenarios("features/match_queries.feature")


@given("the match data is loaded", target_fixture="svc")
def given_match_data(service: SoccerDataService):
    return service


@when(parsers.parse('I search for matches between "{team}" and "{opponent}"'),
      target_fixture="result")
def when_search_between(svc, team, opponent):
    return svc.search_matches(team=team, opponent=opponent, limit=500)


@when(parsers.parse('I request statistics for "{team}" in season {season}'),
      target_fixture="result")
def when_team_stats(svc, team, season):
    return svc.team_stats(team=team, season=int(season))


@when(parsers.parse('I search for matches of team "{team}" in season {season}'),
      target_fixture="result")
def when_search_team_season(svc, team, season):
    return svc.search_matches(team=team, season=int(season), limit=200)


@when(parsers.parse('I search for finals of competition "{competition}"'),
      target_fixture="result")
def when_search_finals(svc, competition):
    return svc.search_matches(competition=competition, stage="final", limit=500)


@when(parsers.parse('I search for matches from "{date_from}" to "{date_to}" '
                    'in competition "{competition}" and season {season}'),
      target_fixture="result")
def when_search_date_range(svc, date_from, date_to, competition, season):
    return svc.search_matches(
        competition=competition, season=int(season),
        date_from=date_from, date_to=date_to, limit=500,
    )


@when(parsers.parse('I search for matches of team "{team}"'),
      target_fixture="result")
def when_search_team(svc, team):
    return svc.search_matches(team=team)


@then("I should receive a list of matches")
def then_list_of_matches(result):
    assert "error" not in result
    assert result["total"] > 0
    assert isinstance(result["matches"], list)
    assert result["matches"]


@then("each match should have date, scores, and competition")
def then_match_fields(result):
    for match in result["matches"]:
        assert match["date"], match
        assert match["home_goals"] is not None, match
        assert match["away_goals"] is not None, match
        assert match["competition"], match


@then("I should receive wins, losses, draws, and goals")
def then_record_fields(result):
    assert "error" not in result
    for section in ("overall", "home", "away"):
        record = result[section]
        for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
            assert field in record, f"{section}.{field} missing"


@then("the totals should be consistent")
def then_totals_consistent(result):
    overall = result["overall"]
    assert overall["wins"] + overall["draws"] + overall["losses"] == overall["matches"]
    assert result["home"]["matches"] + result["away"]["matches"] == overall["matches"]


@then(parsers.parse('every match should involve the team "{team}"'))
def then_every_match_involves(result, svc, team):
    resolution = svc.resolve_team(team)
    assert resolution["found"]
    for match in result["matches"]:
        assert match["home_key"] == resolution["key"] or \
            match["away_key"] == resolution["key"], match


@then(parsers.parse("every match should be from season {season}"))
def then_every_match_season(result, season):
    for match in result["matches"]:
        assert match["season"] == int(season), match


@then(parsers.parse('every match should be from competition "{competition}"'))
def then_every_match_competition(result, competition):
    for match in result["matches"]:
        assert competition in match["competition"], match


@then("each season should contribute at most 2 finals")
def then_finals_per_season(result):
    seasons = [match["season"] for match in result["matches"]]
    assert seasons
    for season in set(seasons):
        assert seasons.count(season) <= 2, season


@then(parsers.parse("the dataset should contain {count} finals"))
def then_finals_count(result, count):
    assert result["total"] == int(count)
    assert len(result["matches"]) == int(count)


@then("every match should fall within the date range")
def then_date_range(result):
    for match in result["matches"]:
        assert "2019-11-01" <= match["date"] <= "2019-11-30", match


@then("the result should not be empty")
def then_not_empty(result):
    assert "error" not in result
    assert result["total"] > 0


@then(parsers.parse('the last match should be on "{date}"'))
def then_last_match_date(result, date):
    assert result["last_match"].startswith(date), result["last_match"]


@then("the last match should have a score")
def then_last_match_score(result):
    last = result["matches"][-1]
    assert last["home_goals"] is not None
    assert last["away_goals"] is not None


@then("the response should explain the team was not found")
def then_team_not_found(result):
    assert "error" in result
    assert "not found" in result["error"]
