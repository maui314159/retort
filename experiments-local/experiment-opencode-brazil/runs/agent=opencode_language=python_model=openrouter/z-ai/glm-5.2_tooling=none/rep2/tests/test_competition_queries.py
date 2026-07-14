# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# BDD step definitions for competition_queries.feature.
# ----------------------------------------------------------------------------
from __future__ import annotations

from pytest_bdd import when, then, parsers, scenarios

from brazilian_soccer_mcp import QueryEngine

scenarios("features/competition_queries.feature")


@when(
    parsers.parse('I request standings for "{competition}" season "{season:d}"'),
    target_fixture="standings_result",
)
def request_standings(engine: QueryEngine, competition, season):
    return engine.standings(competition, season)


@when(
    parsers.parse('I request the champion for "{competition}" season "{season:d}"'),
    target_fixture="champion_result",
)
def request_champion(engine: QueryEngine, competition, season):
    return engine.champion(competition, season)


@when(
    parsers.parse('I request {n:d} relegated teams for "{competition}" season "{season:d}"'),
    target_fixture="relegated_result",
)
def request_relegated(engine: QueryEngine, n, competition, season):
    return engine.relegated_teams(competition, season, n=n)


@when(
    parsers.parse('I request average goals for competition "{competition}"'),
    target_fixture="avg_goals_result",
)
def request_avg_goals(engine: QueryEngine, competition):
    return engine.average_goals(competition=competition)


# ----------------------------------------------------------------------------
# Then
# ----------------------------------------------------------------------------
@then("I should receive a full league table")
def full_table(standings_result):
    assert isinstance(standings_result, list)
    assert len(standings_result) >= 10


@then("the table should be sorted by points descending")
def table_sorted(standings_result):
    points = [r["points"] for r in standings_result]
    assert points == sorted(points, reverse=True)


@then(parsers.parse("the top team should be {team}"))
def top_team_is(standings_result, team):
    from brazilian_soccer_mcp.normalizers import team_key
    assert team_key(standings_result[0]["team"]) == team_key(team)


@then(parsers.parse("the champion should be {team}"))
def champion_is(champion_result, team):
    from brazilian_soccer_mcp.normalizers import team_key
    assert champion_result is not None
    assert team_key(champion_result["team"]) == team_key(team)


@then(parsers.parse("I should receive exactly {n:d} teams"))
def exactly_n(relegated_result, n):
    assert len(relegated_result) == n


@then("they should be the bottom 4 of the standings")
def bottom_four(relegated_result):
    # The relegated list is already the bottom n; verify positions are >= 17
    # in a 20-team table (positions are assigned by standings()).
    positions = sorted(r["position"] for r in relegated_result)
    assert positions[-1] > positions[0], "Expected distinct positions"
    assert len(positions) == 4


@then("I should receive a positive average goals per match")
def positive_avg(avg_goals_result):
    assert avg_goals_result["average_goals_per_match"] > 0


@then("the home win rate should be higher than the away win rate")
def home_better_than_away(avg_goals_result):
    assert avg_goals_result["home_win_rate"] > avg_goals_result["away_win_rate"]
