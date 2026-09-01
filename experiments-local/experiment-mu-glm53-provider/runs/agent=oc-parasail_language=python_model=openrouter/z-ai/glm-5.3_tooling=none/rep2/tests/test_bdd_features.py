"""BDD step definitions for the Gherkin feature files.

All scenarios in ``tests/features/*.feature`` are bound here and share the
session-scoped engine fixture (data loads once per test session).
"""

from __future__ import annotations

import asyncio
import json

from pytest_bdd import given, parsers, scenarios, then, when

from soccer_mcp.engine import SoccerData

scenarios("features")


# ---------------------------------------------------------------- Given


@given("the match data is loaded", target_fixture="engine")
def given_match_data(engine: SoccerData):
    assert engine.matches, "match data must be loaded"
    return engine


@given("the FIFA player data is loaded", target_fixture="engine")
def given_player_data(engine: SoccerData):
    assert engine.players, "player data must be loaded"
    return engine


@given("the knowledge graph is built", target_fixture="engine")
def given_knowledge_graph(engine: SoccerData):
    assert engine.kg.stats()["nodes"] > 0
    return engine


@given("the MCP server is running", target_fixture="mcp_server")
def given_mcp_server(mcp_server):
    return mcp_server


# ---------------------------------------------------------------- When


@when(
    parsers.parse('I search for matches between "{team_a}" and "{team_b}"'),
    target_fixture="result",
)
def when_search_between(engine, team_a, team_b):
    return engine.search_matches(team=team_a, opponent=team_b, limit=500)


@when(
    parsers.re(
        r'I search for matches of "(?P<team>[^"]+)" in competition "(?P<competition>[^"]+)" in season (?P<season>\d+)'
    ),
    target_fixture="result",
)
def when_search_team_season(engine, team, competition, season):
    return engine.search_matches(team=team, competition=competition, season=int(season), limit=500)


@when(
    parsers.re(r'I search for matches of "(?P<team>[^"]+)" in season (?P<season>\d+)'),
    target_fixture="result",
)
def when_search_team_season_only(engine, team, season):
    return engine.search_matches(team=team, season=int(season), limit=500)


@when(
    parsers.parse('I search for Libertadores matches in stage "{stage}" in season {season:d}'),
    target_fixture="result",
)
def when_search_stage(engine, stage, season):
    return engine.search_matches(
        competition="Libertadores", stage=stage, season=season, limit=500
    )


@when(
    parsers.parse(
        'I search for matches from "{date_from}" to "{date_to}" in competition "{competition}"'
    ),
    target_fixture="result",
)
def when_search_dates(engine, date_from, date_to, competition):
    return engine.search_matches(
        competition=competition, date_from=date_from, date_to=date_to, limit=500
    )


@when(
    parsers.parse('I request statistics for "{team}" in season "{season}"'),
    target_fixture="result",
)
def when_team_stats(engine, team, season):
    return engine.team_stats(team=team, season=int(season))


@when(
    parsers.parse(
        'I request home statistics for "{team}" in season {season:d} in competition "{competition}"'
    ),
    target_fixture="result",
)
def when_team_stats_home(engine, team, season, competition):
    return engine.team_stats(team=team, season=season, competition=competition, venue="home")


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'), target_fixture="result")
def when_head_to_head(engine, team_a, team_b):
    return engine.head_to_head(team_a=team_a, team_b=team_b)


@when(
    parsers.parse("I request the best away records with at least {minimum:d} matches"),
    target_fixture="result",
)
def when_best_away(engine, minimum):
    return engine.best_records(venue="away", minimum_matches=minimum, limit=10)


@when(parsers.parse('I request the profile of "{team}"'), target_fixture="result")
def when_team_profile(engine, team):
    return engine.team_profile(team=team)


@when(parsers.parse('I search for players named "{name}"'), target_fixture="result")
def when_search_player(engine, name):
    return engine.search_players(name=name, limit=200)


@when(parsers.parse('I request the top {n:d} players of nationality "{nationality}"'), target_fixture="result")
def when_top_players(engine, n, nationality):
    return engine.top_players(nationality=nationality, limit=n)


@when(parsers.parse('I search for players at club "{club}"'), target_fixture="result")
def when_players_at_club(engine, club):
    return engine.search_players(club=club, limit=100)


@when(
    parsers.parse("I search for Brazilian goalkeepers with overall at least {rating:d}"),
    target_fixture="result",
)
def when_brazilian_gks(engine, rating):
    return engine.search_players(
        nationality="Brazil", position="GK", min_overall=rating, limit=50
    )


@when(parsers.parse('I request the "{competition}" standings for {season:d}'), target_fixture="result")
def when_standings(engine, competition, season):
    return engine.standings(competition=competition, season=season)


@when(parsers.parse('I request the "{competition}" finals'), target_fixture="result")
def when_finals(engine, competition):
    return engine.competition_finals(competition=competition)


@when("I request the competition information", target_fixture="result")
def when_competition_info(engine):
    return engine.competition_info()


@when(parsers.parse('I request goal averages for "{competition}"'), target_fixture="result")
def when_goal_averages_comp(engine, competition):
    return engine.goal_averages(competition=competition)


@when("I request goal averages for all competitions", target_fixture="result")
def when_goal_averages_all(engine):
    return engine.goal_averages()


@when(parsers.parse("I request the {n:d} biggest wins"), target_fixture="result")
def when_biggest_wins(engine, n):
    return engine.biggest_wins(limit=n)


@when(parsers.parse("I request the derbies of season {season:d}"), target_fixture="result")
def when_derbies(engine, season):
    return engine.derbies(season=season)


@when(
    parsers.parse('I request the top scoring teams for "{competition}" in {season:d}'),
    target_fixture="result",
)
def when_top_scoring(engine, competition, season):
    return engine.top_scoring_teams(competition=competition, season=season)


@when("I request the graph overview", target_fixture="result")
def when_graph_overview(engine):
    return engine.graph_overview()


@when(parsers.parse('I request the team graph for "{team}"'), target_fixture="result")
def when_team_graph(engine, team):
    return engine.team_graph(team=team)


@when(parsers.parse('I request paths between "{a}" and "{b}"'), target_fixture="result")
def when_graph_paths(engine, a, b):
    return engine.graph_paths(entity_a=a, entity_b=b)


@when("I list the available tools", target_fixture="tool_names")
def when_list_tools(mcp_server):
    async def _list():
        tools = await mcp_server.list_tools()
        return [t.name for t in tools]

    return asyncio.run(_list())


@when(
    parsers.parse('I call the "{tool}" tool with competition "{competition}" and season {season:d}'),
    target_fixture="tool_response",
)
def when_call_standings_tool(mcp_server, tool, competition, season):
    async def _call():
        result = await mcp_server.call_tool(
            tool, {"competition": competition, "season": season}
        )
        return json.loads(result.content[0].text)

    return asyncio.run(_call())


@when(parsers.parse('I call the "{tool}" tool with name "{name}"'), target_fixture="tool_response")
def when_call_search_players(mcp_server, tool, name):
    async def _call():
        result = await mcp_server.call_tool(tool, {"name": name})
        return json.loads(result.content[0].text)

    return asyncio.run(_call())


@when(parsers.parse('I call the "{tool}" tool with team "{team}"'), target_fixture="tool_response")
def when_call_team_tool(mcp_server, tool, team):
    async def _call():
        result = await mcp_server.call_tool(tool, {"team": team})
        return json.loads(result.content[0].text)

    return asyncio.run(_call())


# ---------------------------------------------------------------- Then


@then("I should receive a list of matches")
def then_matches_list(result):
    assert "error" not in result, result.get("error")
    assert result["total_matches"] > 0
    assert result["matches"], "at least one match should be returned"


@then("each match should have date, scores, and competition")
def then_match_fields(result):
    for match in result["matches"]:
        assert match["date"] is not None
        assert match["score"] != "not recorded"
        assert match["competition"]


@then("only Flamengo and Fluminense should be involved")
def then_only_two_teams(result):
    for match in result["matches"]:
        teams = {match["home_team_id"], match["away_team_id"]}
        assert teams == {"flamengo", "fluminense"}


@then("every match should involve Palmeiras")
def then_involves_palmeiras(result):
    for match in result["matches"]:
        assert "palmeiras" in (match["home_team_id"], match["away_team_id"])


@then("every match should be from the 2023 Brasileirão Série A")
def then_2023_serie_a(result):
    for match in result["matches"]:
        assert match["season"] == 2023
        assert match["competition"] == "Brasileirão Série A"


@then("every match should be a final")
def then_stage_final(result):
    assert result["total_matches"] > 0
    for match in result["matches"]:
        assert match["stage"] == "final"


@then("the 2019 final should be Flamengo 2-1 River Plate")
def then_2019_final(result):
    assert result["total_matches"] == 1
    match = result["matches"][0]
    assert match["home_team"] == "Flamengo (RJ)"
    assert match["away_team"] == "River Plate"
    assert match["score"] == "2-1"


@then("every match should be dated within June 2019")
def then_june_2019(result):
    assert result["total_matches"] > 0
    for match in result["matches"]:
        assert match["date"].startswith("2019-06")


@then("every match should be a Copa do Brasil match")
def then_cup_matches(result):
    for match in result["matches"]:
        assert match["competition"] == "Copa do Brasil"


@then("both searches should return the same number of matches")
def then_same_count(engine, result):
    other = engine.search_matches(team="CR Flamengo", season=2012, limit=500)
    assert other["total_matches"] == result["total_matches"] > 0


@then("I should receive wins, losses, draws, and goals")
def then_record_fields(result):
    record = result["record"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in record
    assert record["matches"] > 0


@then("the record should show 19 home matches")
def then_19_matches(result):
    assert result["record"]["matches"] == 19


@then("the record should show 12 wins, 4 draws and 3 losses")
def then_12_4_3(result):
    record = result["record"]
    assert (record["wins"], record["draws"], record["losses"]) == (12, 4, 3)


@then("the summary should contain the win rate")
def then_win_rate_in_summary(result):
    assert "Win rate" in result["summary"]


@then("I should receive wins, draws and losses for both teams")
def then_h2h_fields(result):
    for key in ("team_a", "team_b"):
        for stat in ("wins", "draws", "losses", "goals_for", "goals_against"):
            assert stat in result[key]


@then("the match counts of both teams should be equal")
def then_h2h_counts(result):
    assert result["team_a"]["matches"] == result["team_b"]["matches"]
    assert result["total_matches"] == result["team_a"]["matches"]


@then("Palmeiras should have 17 wins and Santos 16 wins with 8 draws")
def then_h2h_numbers(result):
    assert result["team_a"]["wins"] == 17
    assert result["team_b"]["wins"] == 16
    assert result["team_a"]["draws"] == 8


@then("the ranking should be sorted by win rate descending")
def then_ranked_by_win_rate(result):
    rates = [team["win_rate"] for team in result["ranking"]]
    assert rates == sorted(rates, reverse=True)


@then("every ranked team should have at least 50 away matches")
def then_min_matches(result, minimum=50):
    for team in result["ranking"]:
        assert team["matches"] >= 50


@then("the profile should list multiple competitions")
def then_profile_competitions(result):
    assert len(result["competitions"]) >= 3
    names = [entry["competition"] for entry in result["competitions"]]
    assert "Brasileirão Série A" in names


@then("the profile should include an overall record")
def then_profile_record(result):
    assert result["overall_record"]["matches"] > 0


@then(parsers.parse('the results should include "{name}"'))
def then_player_in_results(result, name):
    names = [p["name"] for p in result["players"]]
    assert name in names


@then("he should be Brazilian with overall rating 92")
def then_neymar_details(result):
    neymar = next(p for p in result["players"] if p["name"] == "Neymar Jr")
    assert neymar["nationality"] == "Brazil"
    assert neymar["overall"] == 92


@then(parsers.parse('the top rated player should be "{name}"'))
def then_top_player(result, name):
    assert result["players"][0]["name"] == name


@then("every listed player should be Brazilian")
def then_all_brazilian(result):
    assert result["players"]
    for player in result["players"]:
        assert player["nationality"] == "Brazil"


@then("the players should be sorted by overall rating descending")
def then_players_sorted(result):
    ratings = [p["overall"] for p in result["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then("at least 20 players should be found")
def then_20_players(result):
    assert result["total_players"] >= 20


@then("every player should play for Grêmio")
def then_gremio_players(result):
    for player in result["players"]:
        assert "Grêmio" in player["club"]


@then("every player should be a Brazilian goalkeeper rated at least 85")
def then_gk_filter(result):
    assert result["players"]
    for player in result["players"]:
        assert player["nationality"] == "Brazil"
        assert player["position"] == "GK"
        assert player["overall"] >= 85


@then("Alisson should be among the results")
def then_allisson(result):
    names = [p["name"] for p in result["players"]]
    assert "Alisson" in names


@then("zero players should be found and the answer should say so gracefully")
def then_zero_players(result):
    assert result["total_players"] == 0
    assert "0 player" in result["summary"]


@then("the champion should be Flamengo with 90 points")
def then_champion_flamengo(result):
    assert result["champion"]["team"] == "Flamengo (RJ)"
    assert result["champion"]["points"] == 90


@then("the top three should be Flamengo, Santos and Palmeiras")
def then_top_three(result):
    top3 = [row["team"] for row in result["table"][:3]]
    assert top3 == ["Flamengo (RJ)", "Santos (SP)", "Palmeiras (SP)"]


@then("the table should list 20 teams")
def then_20_teams(result):
    assert len(result["table"]) == 20


@then("the season should be complete with 380 matches")
def then_complete_380(result):
    assert result["completeness"] == "complete"
    assert result["matches_counted"] == 380


@then("the relegated teams should be Coritiba, Vasco, Goiás and Botafogo")
def then_relegated_2020(result):
    relegated = {row["team"] for row in result["relegated"]}
    assert relegated == {"Coritiba (PR)", "Vasco da Gama (RJ)", "Goiás (GO)", "Botafogo (RJ)"}


@then("the 2012 final should be won by Palmeiras against Coritiba")
def then_2012_final(result):
    final_2012 = next(f for f in result["finals"] if f["season"] == 2012)
    assert final_2012["winner"] == "Palmeiras (SP)"
    assert "Coritiba" in final_2012["final"]


@then("the 2015 final should be decided on penalties")
def then_2015_final(result):
    final_2015 = next(f for f in result["finals"] if f["season"] == 2015)
    assert final_2015["winner"] is None
    assert "penalties" in final_2015["winner_note"]


@then("the 2019 final should be won by Flamengo against River Plate")
def then_2019_lib_final(result):
    final_2019 = next(f for f in result["finals"] if f["season"] == 2019)
    assert final_2019["winner"] == "Flamengo (RJ)"
    assert "River Plate" in final_2019["final"]


@then("I should receive an error explaining standings apply to leagues")
def then_standings_leagues_only(result):
    assert "error" in result
    assert "league" in result["error"].lower()


@then("Série A, Série B, Série C, Copa do Brasil and Libertadores should be listed")
def then_all_competitions(result):
    names = set(result["competitions"])
    assert names == {"serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"}


@then("each competition should cover multiple seasons")
def then_multi_seasons(result):
    for entry in result["competitions"].values():
        assert len(entry["seasons"]) >= 2


@then("the average goals per match should be between 2.0 and 3.0")
def then_avg_goals(result):
    assert 2.0 <= result["average_goals_per_match"] <= 3.0


@then("the home win rate should exceed the away win rate")
def then_home_advantage(result):
    assert result["home_win_rate"] > result["away_win_rate"]


@then("more than 40 percent of matches should be home wins")
def then_home_40(result):
    assert result["home_win_rate"] > 40


@then("fewer than 35 percent of matches should be away wins")
def then_away_35(result):
    assert result["away_win_rate"] < 35


@then("the largest victory margin should be at least 8 goals")
def then_margin_8(result):
    assert result["matches"][0]["goal_margin"] >= 8


@then("the matches should be sorted by margin descending")
def then_margin_sorted(result):
    margins = [m["goal_margin"] for m in result["matches"]]
    assert margins == sorted(margins, reverse=True)


@then("every match should be between traditional rivals")
def then_rivals(result):
    assert result["total_matches"] > 0
    assert len(result["tracked_derbies"]) >= 10


@then("the Fla-Flu derby should appear")
def then_fla_flu(result):
    assert any(m["derby"] == "Fla-Flu" for m in result["matches"])


@then("the Choque-Rei derby should appear")
def then_choque_rei(result):
    assert any(m["derby"] == "Choque-Rei" for m in result["matches"])


@then("Flamengo should be among the top scoring teams")
def then_flamengo_top_scorer(result):
    teams = [entry["team"] for entry in result["teams"]]
    assert "Flamengo (RJ)" in teams


@then("the graph should contain match, club, player and competition nodes")
def then_graph_nodes(result):
    types = result["node_types"]
    for expected in ("match", "club", "player", "competition"):
        assert types.get(expected, 0) > 0


@then("the edge counts should include played_home and plays_for relations")
def then_graph_edges(result):
    edges = result["edge_types"]
    assert edges.get("played_home", 0) > 0
    assert edges.get("plays_for", 0) > 0


@then("the result should include competitions Palmeiras played in")
def then_team_graph_competitions(result):
    assert result["competitions"]
    assert "Brasileirão Série A" in result["competitions"]


@then("the result should include the most frequent opponents")
def then_team_graph_opponents(result):
    assert result["top_opponents"]


@then("Flamengo should be among the opponents")
def then_flamengo_opponent(result):
    opponents = {entry["team"] for entry in result["top_opponents"]}
    assert "Flamengo (RJ)" in opponents


@then("a connection through the Brazil country node should be found")
def then_path_via_brazil(result):
    assert result["paths"], "at least one connection should exist"
    assert any("Brazil" in path for path in result["paths"])


@then("a two-hop connection through a match node should be found")
def then_two_hop(result):
    assert result["paths"]
    two_hop = [p for p in result["paths"] if p.count("-->") == 2]
    assert two_hop
    assert any("[~played_home]" in p or "[played_home]" in p for p in two_hop)


@then("at least 19 tools should be available")
def then_19_tools(tool_names):
    assert len(tool_names) >= 19


@then("tools for matches, players, standings, statistics and the graph should be present")
def then_expected_tools(tool_names):
    expected = {
        "search_matches",
        "head_to_head",
        "team_stats",
        "search_players",
        "top_players",
        "standings",
        "goal_averages",
        "biggest_wins",
        "graph_overview",
    }
    assert expected <= set(tool_names)


@then("the tool should return a JSON document with a summary")
def then_tool_summary(tool_response):
    assert "summary" in tool_response
    assert tool_response["summary"]


@then("the summary should name Flamengo as champion")
def then_tool_champion(tool_response):
    assert "Flamengo" in tool_response["summary"]
    assert "Champion" in tool_response["summary"]


@then("the tool should return Neymar Jr with overall rating 92")
def then_tool_neymar(tool_response):
    neymar = next(p for p in tool_response["players"] if p["name"] == "Neymar Jr")
    assert neymar["overall"] == 92


@then("the tool should return an error message rather than crashing")
def then_tool_error(tool_response):
    assert "error" in tool_response


@then("the response should suggest Flamengo as a candidate")
def then_tool_candidates(tool_response):
    assert "error" in tool_response
    assert any("Flamengo" in c["name"] for c in tool_response["candidates"])
