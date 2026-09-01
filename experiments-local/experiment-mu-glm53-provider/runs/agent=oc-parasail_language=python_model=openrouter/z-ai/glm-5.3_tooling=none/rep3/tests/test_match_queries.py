"""BDD steps for match_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import brazilian_soccer.analysis as an

scenarios("features/match_queries.feature")


@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_between(dataset, ctx, team_a, team_b):
    ctx["result"] = an.search_matches(data=dataset, team=team_a, opponent=team_b, limit=50)


@when(parsers.parse('I search for matches of team "{team}" in season "{season}"'))
def search_team_season(dataset, ctx, team, season):
    ctx["result"] = an.search_matches(data=dataset, team=team, season=int(season), limit=500)


@when(parsers.parse('I search for matches of team "{team}" in competition "{competition}"'))
def search_team_competition(dataset, ctx, team, competition):
    ctx["result"] = an.search_matches(data=dataset, team=team, competition=competition, limit=500)


@when(parsers.parse('I search for matches between dates "{start}" and "{end}"'))
def search_date_range(dataset, ctx, start, end):
    ctx["result"] = an.search_matches(data=dataset, date_from=start, date_to=end, limit=500)


@when(parsers.parse('I request the last match between "{team_a}" and "{team_b}"'))
def last_match(dataset, ctx, team_a, team_b):
    ctx["last_match"] = an.last_match_between(dataset, team_a, team_b)


@when(parsers.parse('I search for matches of team "{team}"'))
def search_unknown_team(dataset, ctx, team):
    try:
        an.search_matches(data=dataset, team=team)
        ctx["error"] = None
    except an.AnalysisError as exc:
        ctx["error"] = str(exc)


@when(parsers.parse('I list the finals of the "{competition}"'))
def list_finals(dataset, ctx, competition):
    ctx["finals"] = an.competition_finals(dataset, competition)


@then("I should receive a list of matches")
def received_matches(ctx):
    assert ctx["result"].total > 0
    assert len(ctx["result"].matches) > 0


@then("each match should have date, scores, and competition")
def match_fields(ctx):
    for m in ctx["result"].matches:
        assert m.date is not None, f"missing date: {m}"
        assert m.home_team and m.away_team
        assert isinstance(m.home_goals, int) and isinstance(m.away_goals, int)
        assert m.home_goals >= 0 and m.away_goals >= 0
        assert m.competition in {
            "Brasileirão Serie A",
            "Brasileirão Serie B",
            "Brasileirão Serie C",
            "Copa do Brasil",
            "Copa Libertadores",
        }


@then(parsers.parse('some matches should have "{team}" at home'))
def some_home(ctx, team):
    from brazilian_soccer.normalize import fold

    assert any(fold(m.home_team) == fold(team) for m in ctx["result"].matches)


@then("all returned matches should involve \"Palmeiras\"")
def all_involve_palmeiras(ctx):
    result = ctx["result"]
    key = result.team.key
    assert all(m.involves(key) for m in result.matches)


@then("all returned matches should be from season 2023")
def all_season_2023(ctx):
    assert all(m.season == 2023 for m in ctx["result"].matches)


@then("more than 30 matches should be found")
def more_than_30(ctx):
    assert ctx["result"].total > 30


@then("all returned matches should be from the Libertadores")
def all_libertadores(ctx):
    assert all(m.competition_id == "libertadores" for m in ctx["result"].matches)


@then("all returned matches should fall within the date range")
def within_date_range(ctx):
    from datetime import date

    start, end = date(2023, 6, 1), date(2023, 6, 15)
    assert all(start <= m.date <= end for m in ctx["result"].matches)


@then("the search should find at least 20 matches")
def at_least_20(ctx):
    assert ctx["result"].total >= 20


@then("I should receive a single match")
def single_match(ctx):
    assert ctx["last_match"] is not None


@then("the match should have a score")
def match_has_score(ctx):
    m = ctx["last_match"]
    assert m.home_goals >= 0 and m.away_goals >= 0
    assert m.score


@then("the search should fail with a helpful message")
def fails_helpfully(ctx):
    assert ctx["error"] is not None
    assert "No team matching" in ctx["error"]


@then("finals from several seasons should be returned")
def several_finals(ctx):
    assert len(ctx["finals"]) >= 5
    seasons = {f.season for f in ctx["finals"]}
    assert len(seasons) >= 5


@then(parsers.parse('the 2012 final should be between "{team_a}" and "{team_b}"'))
def final_2012(ctx, team_a, team_b):
    from brazilian_soccer.normalize import fold

    final_2012 = next(f for f in ctx["finals"] if f.season == 2012)
    teams = set()
    for m in final_2012.matches:
        teams.update({fold(m.home_team), fold(m.away_team)})
    assert {fold(team_a), fold(team_b)} == teams
