"""BDD steps for the Team Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.service import SoccerDataService

scenarios("features/team_queries.feature")


@given("the match data is loaded", target_fixture="svc")
def given_match_data(service: SoccerDataService):
    return service


@when(parsers.parse('I request statistics for "{team}" in season {season}'),
      target_fixture="result")
def when_team_stats(svc, team, season):
    return svc.team_stats(team=team, season=int(season))


@when(parsers.parse('I request home statistics for "{team}" in season {season}'),
      target_fixture="result")
def when_home_stats(svc, team, season):
    return svc.team_stats(team=team, season=int(season),
                          competition="Brasileirão Série A", venue="home")


@when(parsers.parse('I compare "{team}" and "{opponent}" head-to-head'),
      target_fixture="result")
def when_head_to_head(svc, team, opponent):
    return svc.head_to_head(team=team, opponent=opponent)


@when(parsers.parse('I list the competitions of "{team}"'),
      target_fixture="result")
def when_team_competitions(svc, team):
    return svc.team_competitions(team)


@when(parsers.parse('I resolve the team name "{name}"'),
      target_fixture="result")
def when_resolve_team(svc, name):
    return svc.resolve_team(name)


@when(parsers.parse('I request statistics for "{team}"'),
      target_fixture="result")
def when_stats_all(svc, team):
    return svc.team_stats(team=team)


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


@then(parsers.parse("the record should count {count} played matches"))
def then_record_matches(result, count):
    assert result["overall"]["matches"] == int(count)


@then("I should receive their matches and an all-time record")
def then_h2h_shape(result):
    assert "error" not in result
    assert result["total_matches"] > 0
    assert result["matches"]
    summary = result["summary"]
    for field in ("team_wins", "opponent_wins", "draws", "team_goals",
                  "opponent_goals"):
        assert field in summary


@then("the record should account for every played match")
def then_h2h_accounting(result):
    summary = result["summary"]
    assert summary["matches"] == summary["team_wins"] + summary["opponent_wins"] \
        + summary["draws"]
    played = [m for m in result["matches"] if m["home_goals"] is not None]
    assert len(played) == min(summary["matches"], 30)


@then(parsers.parse("the team should appear in {count} competitions"))
def then_team_competitions_count(result, count):
    assert "error" not in result
    assert len(result["competitions"]) == int(count)


@then(parsers.parse('one of them should be "{competition}"'))
def then_competition_present(result, competition):
    names = [entry["competition"] for entry in result["competitions"]]
    assert competition in names


@then(parsers.parse('it should resolve to the canonical team "{display}"'))
def then_resolves_to(result, display):
    assert result["found"] is True
    assert result["display"] == display


@then(parsers.parse('it should resolve to the most frequent "{key}"'))
def then_resolves_key(result, key):
    assert result["found"] is True
    assert result["key"] == key.lower()


@then("the alternatives should mention Atletico-PR")
def then_alternatives_atletico_pr(result):
    alternatives = result.get("alternatives", [])
    assert any(alt["key"] == "atletico-pr" for alt in alternatives), alternatives


@then("the by-competition breakdown should include Brasileirão Série A")
def then_breakdown_includes(result):
    names = [entry["competition"] for entry in result["by_competition"]]
    assert "Brasileirão Série A" in names


@then("the overall record should aggregate home and away matches")
def then_overall_aggregates(result):
    assert result["overall"]["matches"] == result["home"]["matches"] + \
        result["away"]["matches"]
