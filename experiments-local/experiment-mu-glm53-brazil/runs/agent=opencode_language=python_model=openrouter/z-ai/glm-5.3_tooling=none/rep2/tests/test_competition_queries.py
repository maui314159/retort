"""BDD steps for the Competition Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.service import SoccerDataService

scenarios("features/competition_queries.feature")


@given("the match data is loaded", target_fixture="svc")
def given_match_data(service: SoccerDataService):
    return service


@when(parsers.parse('I request the standings of "{competition}" season {season}'),
      target_fixture="result")
def when_standings(svc, competition, season):
    return svc.standings(competition=competition, season=int(season))


@when(parsers.parse('I request the standings of "{competition}" without a season'),
      target_fixture="result")
def when_standings_no_season(svc, competition):
    return svc.standings(competition=competition, season=None)


@when("I request competition info", target_fixture="result")
def when_competition_info(svc):
    return svc.competition_info()


@then(parsers.parse('"{team}" should be champion with {points} points'))
def then_champion(result, team, points):
    assert "error" not in result, result
    assert result["champion"] == team
    champion_row = result["table"][0]
    assert champion_row["display"] == team
    assert champion_row["points"] == int(points)


@then("the table should have 20 teams")
def then_twenty_teams(result):
    assert len(result["table"]) == 20


@then("the champion row should read 28 wins 6 draws 4 losses")
def then_champion_row(result):
    champion = result["table"][0]
    assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)


@then("the relegated teams should be Avaí, Chapecoense, CSA and Cruzeiro")
def then_relegated_2019(result):
    assert set(result["relegated"]) == {"Avai", "Chapecoense", "CSA", "Cruzeiro"}


@then(parsers.parse('"{team}" should be second with {points} points'))
def then_runner_up(result, team, points):
    runner_up = result["table"][1]
    assert runner_up["display"] == team
    assert runner_up["points"] == int(points)


@then("the top scoring team should be Grêmio")
def then_top_scorer(result):
    top = max(result["table"], key=lambda row: row["goals_for"])
    assert top["display"] == "Grêmio"


@then("the response should explain that cups have no standings")
def then_no_standings_for_cups(result):
    assert "error" in result
    assert "standings" in result["error"].lower()


@then("the response should list the available seasons")
def then_seasons_listed(result):
    assert "error" in result
    seasons = result["available_seasons"]
    assert 2003 in seasons
    assert 2023 in seasons


@then(parsers.parse("{count} competitions should be described"))
def then_competition_count(result, count):
    assert len(result["competitions"]) == int(count)


@then("the Copa Libertadores should span 2013 to 2022")
def then_libertadores_span(result):
    entry = [c for c in result["competitions"]
             if c["competition"] == "Copa Libertadores"][0]
    assert entry["seasons"][0] == 2013
    assert entry["seasons"][-1] == 2022


@then(parsers.parse("the champion should be {team}"))
def then_champion_team(result, team):
    assert result["champion"] == team
