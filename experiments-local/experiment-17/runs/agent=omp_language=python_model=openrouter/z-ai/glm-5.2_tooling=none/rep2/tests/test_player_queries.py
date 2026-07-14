"""BDD step definitions for player-query scenarios."""

from __future__ import annotations

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer import queries as Q

scenarios("features/player_queries.feature")


@when(parsers.parse('I search for a player named "{name}"'))
def search_by_name(data, ctx, name):
    ctx["players"] = Q.search_players(data, name=name, limit=20)


@when(parsers.parse('I request the top {n:d} players from "{nationality}"'))
def top_players(data, ctx, n, nationality):
    ctx["players"] = Q.top_players(data, nationality=nationality, limit=n)


@when(parsers.parse('I search for "{group}" players limited to {n:d}'))
def search_position_group(data, ctx, group, n):
    ctx["players"] = Q.search_players(data, position_group_name=group, limit=n)


@when(parsers.parse('I request players at club "{club}"'))
def players_at_club(data, ctx, club):
    ctx["players"] = Q.players_at_club(data, club, limit=50)


@then("I should receive a non-empty player list")
def assert_nonempty(ctx):
    assert len(ctx["players"]) > 0


@then("each player should have name, overall, position and club")
def assert_player_fields(ctx):
    for p in ctx["players"]:
        for k in ("Name", "Overall", "Position", "Club"):
            assert k in p, k


@then(parsers.parse("I should receive {n:d} players"))
def assert_count(ctx, n):
    assert len(ctx["players"]) == n, len(ctx["players"])


@then("every player should be Brazilian")
def assert_brazilian(ctx):
    for p in ctx["players"]:
        assert p["Nationality"] == "Brazil", p


@then("the list should be sorted by overall descending")
def assert_sorted(ctx):
    ratings = [p["Overall"] for p in ctx["players"]]
    assert ratings == sorted(ratings, reverse=True), ratings


@then(parsers.parse("I should receive at most {n:d} players"))
def assert_at_most(ctx, n):
    assert len(ctx["players"]) <= n


@then("every player should be a forward")
def assert_forward(ctx):
    from brazilian_soccer.normalize import POSITION_GROUPS
    fwd = POSITION_GROUPS["FWD"]
    for p in ctx["players"]:
        assert p["Position"] in fwd, p


@then(parsers.parse('each player should have a club containing "{text}"'))
def assert_club_contains(ctx, text):
    for p in ctx["players"]:
        assert text.lower() in (p["Club"] or "").lower(), p
