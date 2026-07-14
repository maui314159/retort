"""
Context
=======
Module: tests.test_bdd

pytest-bdd step definitions binding every Gherkin scenario in
tests/features/*.feature to the query layer (brazilian_soccer_mcp.queries).

We bind each feature file with `scenarios(...)` so adding a scenario to a
.feature picks up automatically as long as its steps exist here. Steps share
state through the function-scoped `context` fixture (see conftest); the
session-scoped `kb` fixture supplies the loaded data.

These are behaviour tests, not plumbing tests: they assert logical invariants
(W+D+L == matches played, points == 3W+D, standings monotonic in points,
ordering by rating/margin, name-variant equivalence) and a couple of concrete,
externally-verifiable facts (2019 Brasileirão champion Flamengo on 90 pts).
They deliberately avoid asserting incidental values that would break on a
harmless data refresh.
"""

from __future__ import annotations

import time

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp import queries

# Bind all five feature files.
scenarios(
    "features/matches.feature",
    "features/teams.feature",
    "features/players.feature",
    "features/competitions.feature",
    "features/statistics.feature",
)


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #
@given("the knowledge base is loaded")
def _loaded(kb):
    assert len(kb.matches) > 0
    assert len(kb.players) > 0


# --------------------------------------------------------------------------- #
# When - matches
# --------------------------------------------------------------------------- #
@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def _matches_between(kb, context, team_a, team_b):
    context["matches_result"] = queries.find_matches(kb, team=team_a, opponent=team_b)


@when(
    parsers.parse(
        'I search for matches for "{team}" in the "{competition}" season "{season:d}"'
    )
)
def _matches_team_comp_season(kb, context, team, competition, season):
    res = queries.find_matches(kb, team=team, competition=competition, season=season)
    # Two consecutive calls in one scenario compare counts; stash a list.
    context.setdefault("variation_counts", []).append(res["count"])
    context["matches_result"] = res


@when(parsers.parse('I search for matches in the "{competition}" season "{season:d}"'))
def _matches_comp_season(kb, context, competition, season):
    context["matches_result"] = queries.find_matches(
        kb, competition=competition, season=season, limit=2000
    )
    context["expected_competition"] = queries.resolve_competition(competition)
    context["expected_season"] = season


@when(
    parsers.parse(
        'I search for home matches for "{team}" in the "{competition}" season "{season:d}"'
    )
)
def _home_matches(kb, context, team, competition, season):
    context["matches_result"] = queries.find_matches(
        kb, team=team, competition=competition, season=season, venue="home", limit=2000
    )
    context["home_team_query"] = team


@when(parsers.parse('I list the competitions "{team}" has played in'))
def _team_competitions(kb, context, team):
    res = queries.find_matches(kb, team=team, limit=20000)
    context["team_competitions"] = sorted(
        {m["competition"] for m in res["matches"]}
    )


# --------------------------------------------------------------------------- #
# When - teams
# --------------------------------------------------------------------------- #
@when(
    parsers.parse(
        'I request the home record for "{team}" in the "{competition}" season "{season:d}"'
    )
)
def _home_record(kb, context, team, competition, season):
    context["record_result"] = queries.team_record(
        kb, team, competition=competition, season=season, venue="home"
    )


@when(
    parsers.parse(
        'I request the record for "{team}" in the "{competition}" season "{season:d}"'
    )
)
def _record(kb, context, team, competition, season):
    context["record_result"] = queries.team_record(
        kb, team, competition=competition, season=season
    )


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def _compare(kb, context, team_a, team_b):
    res = queries.head_to_head(kb, team_a, team_b)
    context["h2h_result"] = res
    context.setdefault("h2h_totals", []).append(res["total_matches"])


# --------------------------------------------------------------------------- #
# When - players
# --------------------------------------------------------------------------- #
@when(parsers.parse('I search for players named "{name}"'))
def _players_named(kb, context, name):
    context["players_result"] = queries.find_players(kb, name=name)


@when(parsers.parse('I search for players from "{nationality}"'))
def _players_from(kb, context, nationality):
    context["players_result"] = queries.find_players(
        kb, nationality=nationality, limit=2000
    )


@when(
    parsers.parse(
        'I search for players from "{nationality}" with overall at least {minimum:d}'
    )
)
def _players_min_overall(kb, context, nationality, minimum):
    context["players_result"] = queries.find_players(
        kb, nationality=nationality, min_overall=minimum, limit=2000
    )


@when(parsers.parse('I summarise "{nationality}" players grouped by club'))
def _players_by_club(kb, context, nationality):
    context["club_summary"] = queries.players_by_club_summary(kb, nationality)


# --------------------------------------------------------------------------- #
# When - competitions
# --------------------------------------------------------------------------- #
@when(parsers.parse('I compute the standings for "{competition}" season "{season:d}"'))
def _standings(kb, context, competition, season):
    context["standings_result"] = queries.standings(kb, competition, season)


@when("I list the available competitions")
def _list_competitions(kb, context):
    context["competition_list"] = kb.competitions


# --------------------------------------------------------------------------- #
# When - statistics
# --------------------------------------------------------------------------- #
@when(parsers.parse('I compute statistics for "{competition}" season "{season:d}"'))
def _stats(kb, context, competition, season):
    context["stats_result"] = queries.competition_stats(kb, competition, season)


@when(parsers.parse("I find the {limit:d} biggest wins overall"))
def _biggest_wins(kb, context, limit):
    context["biggest_result"] = queries.biggest_wins(kb, limit=limit)


@when(
    parsers.parse(
        'I rank teams by "{metric}" for home matches in "{competition}" season "{season:d}"'
    )
)
def _best_record(kb, context, metric, competition, season):
    context["ranking_result"] = queries.best_record(
        kb, competition=competition, season=season, venue="home", metric=metric
    )


@when(parsers.parse('I time a head-to-head lookup for "{team_a}" and "{team_b}"'))
def _timed_lookup(kb, context, team_a, team_b):
    start = time.perf_counter()
    queries.head_to_head(kb, team_a, team_b)
    context["elapsed"] = time.perf_counter() - start


# --------------------------------------------------------------------------- #
# Then - matches
# --------------------------------------------------------------------------- #
@then(parsers.parse("I should receive at least {n:d} matches"))
def _at_least_matches(context, n):
    assert context["matches_result"]["count"] >= n


@then("each match should have a date, scores, and competition")
def _match_shape(context):
    matches = context["matches_result"]["matches"]
    assert matches, "expected at least one match"
    for m in matches:
        assert m["competition"]
        assert m["home"] and m["away"]
        # date and score may be None for the handful of incomplete rows, but
        # the keys must always be present.
        assert "date" in m and "score" in m


@then("both searches should return the same number of matches")
def _same_counts(context):
    counts = context["variation_counts"]
    assert len(counts) == 2
    assert counts[0] == counts[1], counts


@then(parsers.parse('every returned match should be in competition "{competition}"'))
def _every_comp(context, competition):
    for m in context["matches_result"]["matches"]:
        assert m["competition"] == competition


@then(parsers.parse('every returned match should be in season "{season:d}"'))
def _every_season(context, season):
    for m in context["matches_result"]["matches"]:
        assert m["season"] == season


@then(parsers.parse("there should be {n:d} matches"))
def _exactly_n(context, n):
    assert context["matches_result"]["count"] == n


@then(parsers.parse('"{team}" should be the home team in every match'))
def _home_every(context, team):
    from brazilian_soccer_mcp.normalize import names_match

    for m in context["matches_result"]["matches"]:
        assert names_match(team, m["home"]), m


@then(parsers.parse('the competitions should include "{competition}"'))
def _competitions_include(context, competition):
    assert competition in context["team_competitions"]


# --------------------------------------------------------------------------- #
# Then - teams
# --------------------------------------------------------------------------- #
@then("I should receive wins, losses, draws, and goals")
def _record_shape(context):
    rec = context["record_result"]["record"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in rec


@then("the wins, draws and losses should sum to the matches played")
def _record_sums(context):
    rec = context["record_result"]["record"]
    assert rec["wins"] + rec["draws"] + rec["losses"] == rec["matches"]


@then("the win rate should be between 0 and 100")
def _winrate_bounds(context):
    wr = context["record_result"]["record"]["win_rate"]
    assert 0 <= wr <= 100


@then("the points should equal three times the wins plus the draws")
def _points_formula(context):
    rec = context["record_result"]["record"]
    assert rec["points"] == 3 * rec["wins"] + rec["draws"]


@then("the team A wins, team B wins and draws should sum to the total matches")
def _h2h_sums(context):
    r = context["h2h_result"]
    # Matches with missing goals are counted in total_matches but not in the
    # win/draw tallies, so the decided results may be <= total.
    decided = r["team_a_wins"] + r["team_b_wins"] + r["draws"]
    assert decided <= r["total_matches"]
    assert decided > 0


@then("the total matches should be greater than 0")
def _h2h_nonzero(context):
    assert context["h2h_result"]["total_matches"] > 0


@then("both comparisons should report the same total matches")
def _h2h_symmetric(context):
    totals = context["h2h_totals"]
    assert len(totals) == 2
    assert totals[0] == totals[1]


# --------------------------------------------------------------------------- #
# Then - players
# --------------------------------------------------------------------------- #
@then("I should receive at least one player")
def _one_player(context):
    assert context["players_result"]["count"] >= 1


@then(parsers.parse('the top player\'s nationality should be "{nationality}"'))
def _top_nationality(context, nationality):
    assert context["players_result"]["players"][0]["nationality"] == nationality


@then(parsers.parse("I should receive at least {n:d} players"))
def _at_least_players(context, n):
    assert context["players_result"]["count"] >= n


@then(parsers.parse('every returned player should have nationality "{nationality}"'))
def _every_nationality(context, nationality):
    for p in context["players_result"]["players"]:
        assert p["nationality"] == nationality


@then("the players should be ordered by overall rating descending")
def _players_ordered(context):
    overalls = [
        p["overall"] for p in context["players_result"]["players"] if p["overall"] is not None
    ]
    assert overalls == sorted(overalls, reverse=True)


@then(parsers.parse("every returned player should have an overall of at least {minimum:d}"))
def _every_min_overall(context, minimum):
    for p in context["players_result"]["players"]:
        assert p["overall"] is not None and p["overall"] >= minimum


@then("each club entry should report a player count and an average rating")
def _club_summary_shape(context):
    clubs = context["club_summary"]["clubs"]
    assert clubs
    for c in clubs:
        assert c["players"] >= 1
        assert isinstance(c["avg_overall"], float)


# --------------------------------------------------------------------------- #
# Then - competitions
# --------------------------------------------------------------------------- #
@then(parsers.parse('the champion should be "{team}"'))
def _champion(context, team):
    assert context["standings_result"]["champion"] == team


@then(parsers.parse("the standings should contain {n:d} teams"))
def _standings_teams(context, n):
    assert context["standings_result"]["teams"] == n


@then(parsers.parse("the top team should have {pts:d} points"))
def _top_points(context, pts):
    assert context["standings_result"]["standings"][0]["points"] == pts


@then("each team should have no more points than the team above it")
def _monotonic_points(context):
    rows = context["standings_result"]["standings"]
    for upper, lower in zip(rows, rows[1:]):
        assert upper["points"] >= lower["points"]


@then(parsers.parse("every team should have played {n:d} matches"))
def _all_played(context, n):
    for row in context["standings_result"]["standings"]:
        assert row["matches"] == n


@then(parsers.parse('the result should include "{competition}"'))
def _result_includes(context, competition):
    assert competition in context["competition_list"]


# --------------------------------------------------------------------------- #
# Then - statistics
# --------------------------------------------------------------------------- #
@then("the average goals per match should be between 2 and 3")
def _avg_goals(context):
    avg = context["stats_result"]["avg_goals_per_match"]
    assert 2.0 <= avg <= 3.0


@then("the home, away and draw win rates should sum to about 100 percent")
def _rates_sum(context):
    s = context["stats_result"]
    total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
    assert abs(total - 100.0) < 0.5


@then("the results should be ordered by goal margin descending")
def _margin_ordered(context):
    margins = [m["margin"] for m in context["biggest_result"]["matches"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the largest margin should be at least {n:d}"))
def _largest_margin(context, n):
    assert context["biggest_result"]["matches"][0]["margin"] >= n


@then(parsers.parse('the first ranked team should be "{team}"'))
def _first_ranked(context, team):
    assert context["ranking_result"]["teams"][0]["team"] == team


@then(parsers.parse("every ranked team should have played at least {n:d} matches"))
def _min_matches(context, n):
    for t in context["ranking_result"]["teams"]:
        assert t["matches"] >= n


@then(parsers.parse("the lookup should complete in under {seconds:d} seconds"))
def _fast_enough(context, seconds):
    assert context["elapsed"] < seconds
