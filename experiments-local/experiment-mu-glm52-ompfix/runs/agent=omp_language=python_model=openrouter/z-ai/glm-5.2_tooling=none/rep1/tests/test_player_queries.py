"""
tests.test_player_queries
========================

BDD step definitions for ``features/player_queries.feature``.
"""

from __future__ import annotations

from pytest_bdd import scenarios, when, then

scenarios("features/player_queries.feature")


@when('I search for players named "Neymar"', target_fixture="state")
def search_neymar(state):
    state["result"] = state["engine"].search_players(name="Neymar")
    return state


@when("I request the top Brazilian players", target_fixture="state")
def top_brazilians(state):
    state["result"] = state["engine"].top_brazilian_players(limit=20)
    return state


@when('I search for players at club "Fluminense"', target_fixture="state")
def search_fluminense_players(state):
    state["result"] = state["engine"].top_players_at_club("Fluminense", limit=30)
    return state


@when("I search for forwards", target_fixture="state")
def search_forwards(state):
    state["result"] = state["engine"].search_players(is_forward=True, limit=200)
    return state


@then("I should find at least 1 player")
def at_least_1_player(state):
    r = state["result"]
    assert "Found" in r, f"Expected found players: {r[:200]}"
    # extract the count
    import re
    m = re.search(r"Found (\d+) player", r)
    assert m and int(m.group(1)) >= 1, f"Expected >=1 player: {r[:200]}"


@then("the player should have a name, overall rating, and club")
def player_has_fields(state):
    r = state["result"]
    assert "Overall:" in r, f"Expected overall rating: {r[:200]}"
    assert "Club:" in r, f"Expected club: {r[:200]}"


@then("I should receive a ranked list")
def ranked_list(state):
    r = state["result"]
    assert "1." in r, f"Expected ranked list: {r[:200]}"


@then("the first player should have an overall rating of at least 85")
def first_player_overall_85(state):
    r = state["result"]
    import re
    m = re.search(r"1\..*?Overall: (\d+)", r)
    assert m, f"Expected overall rating for first player: {r[:200]}"
    assert int(m.group(1)) >= 85, f"First player overall < 85: {m.group(1)}"


@then("I should find at least 5 players")
def at_least_5_players(state):
    r = state["result"]
    import re
    m = re.search(r"(\d+)", r)
    # The top_players_at_club output lists players; count numbered lines
    numbered = [l for l in r.split("\n") if l.strip() and l.strip()[0].isdigit()]
    assert len(numbered) >= 5, f"Expected >=5 players, got {len(numbered)}: {r[:200]}"


@then("I should find at least 100 players")
def at_least_100_players(state):
    r = state["result"]
    import re
    m = re.search(r"Found (\d+) player", r)
    assert m and int(m.group(1)) >= 100, f"Expected >=100 players: {r[:200]}"


@then("each player should have a forward position")
def forward_positions(state):
    r = state["result"]
    # result lists players with Position: ST, LW, RW, CF, etc.
    forward_pos = {"ST", "LW", "RW", "CF", "LF", "RF", "RS", "LS"}
    import re
    positions = re.findall(r"Position: (\w+)", r)
    assert positions, f"No positions found: {r[:200]}"
    for p in positions:
        assert p in forward_pos, f"Non-forward position {p}: {r[:200]}"
