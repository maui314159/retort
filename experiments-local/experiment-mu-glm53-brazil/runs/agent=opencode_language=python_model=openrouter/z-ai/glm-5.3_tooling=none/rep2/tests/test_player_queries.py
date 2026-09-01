"""BDD steps for the Player Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.service import SoccerDataService

scenarios("features/player_queries.feature")


@given("the player data is loaded", target_fixture="svc")
def given_player_data(service: SoccerDataService):
    return service


@when(parsers.parse('I search for players named "{name}"'), target_fixture="result")
def when_search_players(svc, name):
    return svc.search_players(name=name, limit=10)


@when(parsers.parse("I request the top {count} Brazilian players"),
      target_fixture="result")
def when_top_brazilian(svc, count):
    return svc.top_players(nationality="Brazil", n=int(count))


@when(parsers.parse('I search for players at club "{club}"'), target_fixture="result")
def when_search_club(svc, club):
    return svc.search_players(club=club, limit=100)


@when(parsers.parse('I search for forwards at club "{club}"'),
      target_fixture="result")
def when_search_forwards(svc, club):
    return svc.search_players(club=club, position="forward", limit=100)


@when("I aggregate Brazilian players by club", target_fixture="result")
def when_players_by_club(svc):
    return svc.players_by_club(nationality="Brazil")


@then(parsers.parse('"{name}" should be found with overall rating {rating}'))
def then_player_rating(result, name, rating):
    matches = [p for p in result["players"] if p["name"] == name]
    assert matches, [p["name"] for p in result["players"]]
    assert matches[0]["overall"] == int(rating)


@then(parsers.parse('"{name}" should lead the list'))
def then_player_leads(result, name):
    assert result["players"], "no players returned"
    assert result["players"][0]["name"] == name


@then("every player should be Brazilian")
def then_all_brazilian(result):
    for player in result["players"]:
        assert player["nationality"] == "Brazil", player


@then(parsers.parse('every result should play for {club}'))
def then_club_players(result, svc, club):
    resolution = svc.resolve_team(club)
    assert resolution["found"]
    for player in result["players"]:
        assert player["club_key"] == resolution["key"], player


@then("every result should be a forward position")
def then_forward_positions(result):
    forward_codes = {"ST", "CF", "LW", "RW"}
    for player in result["players"]:
        assert player["position"] in forward_codes, player


@then("the result should not be empty")
def then_not_empty(result):
    assert "error" not in result
    assert result["total"] > 0


@then("each listed club should be a Brazilian club")
def then_brazilian_clubs(result, svc):
    assert result["clubs"]
    for entry in result["clubs"]:
        resolution = svc.resolve_team(entry["club"])
        assert resolution["found"], entry["club"]
        assert entry["players"] > 0


@then("Santos should be listed with player counts")
def then_santos_listed(result):
    santos = [entry for entry in result["clubs"]
              if entry["club"] in ("Santos", "Santos-SP")]
    assert santos
    assert santos[0]["players"] > 0
    assert santos[0]["avg_overall"] is not None


@then("the result should be an empty list without errors")
def then_empty_graceful(result):
    assert "error" not in result
    assert result["total"] == 0
    assert result["players"] == []
