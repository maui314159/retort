"""BDD test fixtures and step implementations for the Brazilian Soccer MCP.

Context: These tests use pytest-bdd to execute the Gherkin scenarios in the
``features/`` directory against :class:`queries.QueryEngine` and the MCP server
in :mod:`server`. A single module-level :class:`QueryEngine` is built per
session via the ``engine`` fixture so the CSV load cost (~1s) is paid once.

Run::

    pytest -q
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import data_loader
import queries
import server
import asyncio
import os
from datetime import date


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------
scenarios(os.path.join(os.path.dirname(__file__), "..", "features"))


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def store():
    return data_loader.get_store()


@pytest.fixture(scope="session")
def engine(store):
    return queries.QueryEngine(store)


@pytest.fixture(scope="session")
def mcp_server():
    return server.mcp


# Per-scenario result bucket so "When"/"Then" steps can share data without a
# class-based fixture dance.
@pytest.fixture
def ctx():
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------
@given("the match data is loaded", target_fixture="match_data_loaded")
def match_data_loaded(engine):
    assert len(engine._matches) > 1000
    return True


@given("the player data is loaded", target_fixture="player_data_loaded")
def player_data_loaded(engine):
    assert len(engine.store.players) > 1000
    return True


@given("the MCP server is loaded", target_fixture="mcp_loaded")
def mcp_loaded(mcp_server):
    return mcp_server


# ---------------------------------------------------------------------------
# When steps — match queries
# ---------------------------------------------------------------------------
@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'),
      target_fixture="result")
def search_matches_between(engine, ctx, team_a, team_b):
    res = engine.search_matches(team=team_a, opponent=team_b, limit=200)
    ctx["result"] = res
    return res


@when(parsers.parse('I search for matches with competition "{competition}" and season {season:d}'),
      target_fixture="result")
def search_matches_comp_season(engine, ctx, competition, season):
    res = engine.search_matches(competition=competition, season=season, limit=500)
    ctx["result"] = res
    return res


@when(parsers.parse('I search for matches from "{date_from}" to "{date_to}"'),
      target_fixture="result")
def search_matches_date_range(engine, ctx, date_from, date_to):
    res = engine.search_matches(date_from=date_from, date_to=date_to, limit=500)
    ctx["result"] = res
    return res


@when(parsers.parse('I search for "{team}" home matches in season {season:d}'),
      target_fixture="result")
def search_home_matches(engine, ctx, team, season):
    res = engine.search_matches(team=team, venue="home", season=season, limit=500)
    ctx["result"] = res
    return res


@when(parsers.parse("I search for matches with limit {limit:d}"),
      target_fixture="result")
def search_matches_limit(engine, ctx, limit):
    res = engine.search_matches(limit=limit)
    ctx["result"] = res
    return res


# ---------------------------------------------------------------------------
# When steps — team queries
# ---------------------------------------------------------------------------
@when(parsers.parse('I request statistics for "{team}" in season {season:d}'),
      target_fixture="result")
def request_team_stats(engine, ctx, team, season):
    res = engine.team_stats(team, season=season)
    ctx["result"] = res
    # Accumulate so the name-variants scenario can compare two calls.
    ctx.setdefault("results", []).append(res)
    return res


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'),
      target_fixture="result")
def compare_h2h(engine, ctx, team_a, team_b):
    res = engine.head_to_head(team_a, team_b)
    ctx["result"] = res
    return res


@when(parsers.parse("I list competitions for {team}"),
      target_fixture="result")
def list_team_competitions(engine, ctx, team):
    res = engine.team_competitions(team.strip('"'))
    ctx["result"] = res
    return res


# ---------------------------------------------------------------------------
# When steps — player queries
# ---------------------------------------------------------------------------
@when(parsers.parse('I search for players with nationality "{nationality}"'),
      target_fixture="result")
def search_players_nat(engine, ctx, nationality):
    res = engine.search_players(nationality=nationality, limit=100)
    ctx["result"] = res
    return res


@when(parsers.parse("I request the top {n:d} Brazilian players"),
      target_fixture="result")
def top_brazilian(engine, ctx, n):
    res = engine.top_players(nationality="Brazil", limit=n)
    ctx["result"] = res
    return res


@when(parsers.parse('I search for players named "{name}"'),
      target_fixture="result")
def search_players_name(engine, ctx, name):
    res = engine.search_players(name=name, limit=50)
    ctx["result"] = res
    return res


@when(parsers.parse('I search for players with position "{position}"'),
      target_fixture="result")
def search_players_pos(engine, ctx, position):
    res = engine.search_players(position=position, limit=50)
    ctx["result"] = res
    return res


@when("I request Brazilian players grouped by club", target_fixture="result")
def brazilian_by_club(engine, ctx):
    res = engine.brazilian_players_by_club()
    ctx["result"] = res
    return res


# ---------------------------------------------------------------------------
# When steps — competition queries
# ---------------------------------------------------------------------------
@when(parsers.parse('I request standings for "{competition}" season {season:d}'),
      target_fixture="result")
def request_standings(engine, ctx, competition, season):
    res = engine.competition_standings(competition, season=season)
    ctx["result"] = res
    return res


@when(parsers.parse('I request seasons for "{competition}"'),
      target_fixture="result")
def request_seasons(engine, ctx, competition):
    res = engine.competition_seasons(competition)
    ctx["result"] = res
    return res


# ---------------------------------------------------------------------------
# When steps — statistics
# ---------------------------------------------------------------------------
@when(parsers.parse('I request average goals for "{competition}" season {season:d}'),
      target_fixture="result")
def request_avg_goals(engine, ctx, competition, season):
    res = engine.average_goals(competition=competition, season=season)
    ctx["result"] = res
    return res


@when(parsers.parse('I request the {n:d} biggest wins in "{competition}"'),
      target_fixture="result")
def request_biggest_wins(engine, ctx, n, competition):
    res = engine.biggest_wins(competition=competition, limit=n)
    ctx["result"] = res
    return res


@when(parsers.parse('I request the best home record in "{competition}" season {season:d}'),
      target_fixture="result")
def request_best_home(engine, ctx, competition, season):
    res = engine.best_record(venue="home", competition=competition, season=season)
    ctx["result"] = res
    return res


@when(parsers.parse("I request derbies in season {season:d}"),
      target_fixture="result")
def request_derbies(engine, ctx, season):
    res = engine.derbies(season=season)
    ctx["result"] = res
    return res


@when("I request average goals with no filters", target_fixture="result")
def request_avg_goals_all(engine, ctx):
    res = engine.average_goals()
    ctx["result"] = res
    return res


# ---------------------------------------------------------------------------
# When steps — MCP server
# ---------------------------------------------------------------------------
@when(parsers.parse('I call the "{tool}" tool with competition "{competition}" and season {season:d}'),
      target_fixture="result")
def call_tool_standings(mcp_loaded, ctx, tool, competition, season):
    text = asyncio.run(mcp_loaded.call_tool(
        tool, {"competition": competition, "season": season}))
    ctx["result"] = text
    return text


@when(parsers.parse('I call the "{tool}" tool'), target_fixture="result")
def call_tool_simple(mcp_loaded, ctx, tool):
    text = asyncio.run(mcp_loaded.call_tool(tool, {}))
    ctx["result"] = text
    return text


# ---------------------------------------------------------------------------
# Then steps — match queries
# ---------------------------------------------------------------------------
@then("I should receive a list of matches")
def then_list_of_matches(ctx):
    assert ctx["result"]["count"] > 0
    assert len(ctx["result"]["matches"]) > 0


@then("each match should have date, scores, and competition")
def then_match_fields(ctx):
    for m in ctx["result"]["matches"]:
        assert "date" in m
        assert "home_goal" in m
        assert "away_goal" in m
        assert "competition" in m


@then(parsers.parse('every returned match should be from competition "{competition}"'))
def then_match_competition(ctx, competition):
    import normalize as norm
    target = norm.normalize_competition(competition)
    for m in ctx["result"]["matches"]:
        assert m["competition"] == target, \
            f"{m['competition']} != {target}"


@then(parsers.parse("every returned match should be from season {season:d}"))
def then_match_season(ctx, season):
    for m in ctx["result"]["matches"]:
        assert m["season"] == season


@then(parsers.parse('every returned match should be dated between "{d1}" and "{d2}"'))
def then_match_date_range(ctx, d1, d2):
    lo = date.fromisoformat(d1)
    hi = date.fromisoformat(d2)
    for m in ctx["result"]["matches"]:
        assert m["date"], "match has no date"
        md = date.fromisoformat(m["date"])
        assert lo <= md <= hi, f"{md} not in [{lo}, {hi}]"


@then(parsers.parse('every returned match should have "{team}" as the home side'))
def then_match_home_side(ctx, team):
    import normalize as norm
    base, _ = norm.normalize_team(team)
    for m in ctx["result"]["matches"]:
        assert m.get("team_side") == "home", \
            f"team_side was {m.get('team_side')}"


@then(parsers.parse("I should receive at most {n:d} matches"))
def then_at_most_n_matches(ctx, n):
    assert len(ctx["result"]["matches"]) <= n


# ---------------------------------------------------------------------------
# Then steps — team queries
# ---------------------------------------------------------------------------
@then("I should receive wins, losses, draws, and goals")
def then_team_stats_fields(ctx):
    r = ctx["result"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in r


@then("the wins plus draws plus losses should equal the matches played")
def then_team_stats_invariant(ctx):
    r = ctx["result"]
    assert r["wins"] + r["draws"] + r["losses"] == r["matches"]


@then("I should receive the matches played count")
def then_h2h_count(ctx):
    assert "matches_played" in ctx["result"]


@then("the sum of wins and draws should equal the matches played")
def then_h2h_invariant(ctx):
    r = ctx["result"]
    assert r["team_a_wins"] + r["team_b_wins"] + r["draws"] == r["matches_played"]


@then("the statistics should be identical")
def then_stats_identical(ctx):
    results = ctx["results"]
    assert len(results) >= 2
    r1, r2 = results[-2], results[-1]
    # Compare the fields that matter for a team's season record.
    for key in ("matches", "wins", "draws", "losses", "goals_for", "goals_against"):
        assert r1[key] == r2[key], f"{key}: {r1[key]} != {r2[key]}"


@then("the result should include at least one competition")
def then_team_comps(ctx):
    assert len(ctx["result"]["competitions"]) >= 1


# ---------------------------------------------------------------------------
# Then steps — player queries
# ---------------------------------------------------------------------------
@then("every returned player should be Brazilian")
def then_players_brazilian(ctx):
    for p in ctx["result"]["players"]:
        assert p["nationality"].lower() == "brazil", p["name"]


@then("the results should be sorted by overall rating descending")
def then_players_sorted(ctx):
    overalls = [p["overall"] for p in ctx["result"]["players"]]
    assert overalls == sorted(overalls, reverse=True)


@then(parsers.parse("I should receive at most {n:d} players"))
def then_at_most_n_players(ctx, n):
    assert len(ctx["result"]["players"]) <= n


@then("the first player should have the highest overall rating")
def then_first_player_top(ctx):
    players = ctx["result"]["players"]
    assert players
    top = max(p["overall"] for p in players)
    assert players[0]["overall"] == top


@then(parsers.parse('every returned player should have "{fragment}" in their name'))
def then_player_name_contains(ctx, fragment):
    for p in ctx["result"]["players"]:
        assert fragment.lower() in p["name"].lower()


@then(parsers.parse('every returned player should have position "{position}"'))
def then_player_position(ctx, position):
    for p in ctx["result"]["players"]:
        assert p["position"] == position


@then("the result should include a list of clubs with player counts")
def then_clubs_list(ctx):
    assert "clubs" in ctx["result"]
    assert len(ctx["result"]["clubs"]) > 0
    for c in ctx["result"]["clubs"]:
        assert "club" in c and "players" in c


# ---------------------------------------------------------------------------
# Then steps — competition queries
# ---------------------------------------------------------------------------
@then(parsers.parse('the champion should be "{team}"'))
def then_champion(ctx, team):
    assert ctx["result"]["champion"] == team, \
        f"champion was {ctx['result']['champion']}"


@then("the top team should have the most points")
def then_top_team_most_points(ctx):
    standings = ctx["result"]["standings"]
    assert standings
    top_pts = standings[0]["points"]
    for s in standings[1:]:
        assert s["points"] <= top_pts


@then("the positions should start at 1 and increment by 1")
def then_positions_contiguous(ctx):
    positions = [s["position"] for s in ctx["result"]["standings"]]
    assert positions == list(range(1, len(positions) + 1))


@then("each team should have at least as many points as the team below it")
def then_points_ordered(ctx):
    standings = ctx["result"]["standings"]
    for a, b in zip(standings, standings[1:]):
        assert a["points"] >= b["points"]


@then("the result should include a non-empty list of seasons")
def then_seasons_list(ctx):
    assert len(ctx["result"]["seasons"]) > 0


@then(parsers.parse("every team should have played at most {n:d} matches"))
def then_played_at_most(ctx, n):
    for s in ctx["result"]["standings"]:
        assert s["played"] <= n, f"{s['team']} played {s['played']}"


# ---------------------------------------------------------------------------
# Then steps — statistics
# ---------------------------------------------------------------------------
@then(parsers.parse("the average goals per match should be between {lo:f} and {hi:f}"))
def then_avg_range(ctx, lo, hi):
    avg = ctx["result"]["average_goals_per_match"]
    assert lo <= avg <= hi, f"avg {avg} not in [{lo}, {hi}]"


@then("the home win rate plus away win rate plus draw rate should be 100")
def then_rates_sum_100(ctx):
    r = ctx["result"]
    total = round(r["home_win_rate"] + r["away_win_rate"] + r["draw_rate"], 1)
    assert abs(total - 100.0) < 0.2, f"rates sum to {total}"


@then(parsers.parse("I should receive at most {n:d} results"))
def then_at_most_n_wins(ctx, n):
    assert len(ctx["result"]["biggest_wins"]) <= n


@then("each win should have a positive margin")
def then_positive_margin(ctx):
    for w in ctx["result"]["biggest_wins"]:
        assert w["margin"] > 0


@then("the margins should be sorted descending")
def then_margins_sorted(ctx):
    margins = [w["margin"] for w in ctx["result"]["biggest_wins"]]
    assert margins == sorted(margins, reverse=True)


@then("every returned team should have played at least one home match")
def then_best_home_played(ctx):
    for t in ctx["result"]["teams"]:
        assert t["matches"] >= 1


@then("the win rates should be sorted descending")
def then_winrates_sorted(ctx):
    rates = [t["win_rate"] for t in ctx["result"]["teams"]]
    assert rates == sorted(rates, reverse=True)


@then("each derby should involve two different rival teams")
def then_derby_distinct(ctx):
    import normalize as norm
    for d in ctx["result"]["derbies"]:
        hb, _ = norm.normalize_team(d["home_team"])
        ab, _ = norm.normalize_team(d["away_team"])
        assert hb != ab


@then("the matches count should be positive")
def then_matches_positive(ctx):
    assert ctx["result"]["matches"] > 0


# ---------------------------------------------------------------------------
# Then steps — MCP server
# ---------------------------------------------------------------------------
@then(parsers.parse("the server should register at least {n:d} tools"))
def then_at_least_n_tools(mcp_loaded, n):
    tools = asyncio.run(mcp_loaded.list_tools())
    assert len(tools) >= n, f"only {len(tools)} tools"


@then(parsers.parse('the server should register a tool named "{name}"'))
def then_tool_named(mcp_loaded, name):
    tools = asyncio.run(mcp_loaded.list_tools())
    names = {t.name for t in tools}
    assert name in names, f"missing tool {name}; have {names}"


@then(parsers.parse('the response text should mention "{text}"'))
def then_response_mentions(ctx, text):
    content = ctx["result"]
    # call_tool returns a list of TextContent objects.
    if isinstance(content, list):
        text_blob = "\n".join(c.text for c in content)
    else:
        text_blob = str(content)
    assert text in text_blob, f"'{text}' not in response"
