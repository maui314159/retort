"""BDD steps for player_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import brazilian_soccer.analysis as an

scenarios("features/player_queries.feature")


@when(parsers.parse('I search for players of nationality "{nationality}"'))
def search_nationality(dataset, ctx, nationality):
    ctx["players"] = an.search_players(dataset, nationality=nationality, limit=50)


@when(parsers.parse('I search for players of nationality "{nationality}" sorted by rating'))
def search_nationality_sorted(dataset, ctx, nationality):
    ctx["players"] = an.search_players(dataset, nationality=nationality, sort_by="overall", limit=50)


@when(parsers.parse('I search for players at club "{club}"'))
def search_club(dataset, ctx, club):
    ctx["players"] = an.search_players(dataset, club=club, limit=100)


@when(parsers.parse('I search for forwards at club "{club}"'))
def search_forwards(dataset, ctx, club):
    ctx["players"] = an.search_players(dataset, club=club, position="forward", limit=100)


@when(parsers.parse('I look up the player "{name}"'))
def lookup_player(dataset, ctx, name):
    try:
        ctx["details"] = an.player_details(dataset, name)
        ctx["error"] = None
    except an.AnalysisError as exc:
        ctx["details"] = []
        ctx["error"] = str(exc)


@then("more than 800 players should be found")
def more_than_800(ctx):
    assert ctx["players"].total > 800


@then("every player should be Brazilian")
def all_brazilian(ctx):
    assert all(p.nationality == "Brazil" for p in ctx["players"].players)


@then(parsers.parse('the first player should be "{name}"'))
def first_player(ctx, name):
    assert ctx["players"].players[0].name == name


@then(parsers.parse("his overall rating should be {rating:d}"))
def rating_is(ctx, rating):
    assert ctx["players"].players[0].overall == rating


@then("at least 15 players should be found")
def at_least_15(ctx):
    assert ctx["players"].total >= 15


@then("every player should play for Fluminense")
def all_fluminense(ctx):
    assert all(p.club == "Fluminense" for p in ctx["players"].players)


@then("at least 3 players should be found")
def at_least_3(ctx):
    assert ctx["players"].total >= 3


@then("every returned player should be a forward")
def all_forwards(ctx):
    assert all(p.position_group == "Forward" for p in ctx["players"].players)


@then("the player should be found")
def player_found(ctx):
    assert ctx["details"], f"expected a player, got error: {ctx.get('error')}"


@then(parsers.parse('his position should be "{position}"'))
def position_is(ctx, position):
    assert ctx["details"][0].position == position


@then(parsers.parse('his club should be "{club}"'))
def club_is(ctx, club):
    assert ctx["details"][0].club == club


@then("the lookup should report that no player was found")
def no_player(ctx):
    assert ctx["error"] is not None
    assert "No player" in ctx["error"]


@then("the club should also have matches in the match data")
def club_has_matches(dataset, ctx):
    club_key = ctx["players"].club.key
    assert dataset.matches_for_team(club_key), "FIFA club has no matches in match data"
