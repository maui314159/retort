"""Step definitions for player_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, then, when, scenarios

scenarios("features/player_queries.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I search players named "{name}"'))
def search_by_name(engine, context, name):
    context["result"] = engine.search_players(name=name)


@when(parsers.parse('I search players with nationality "{nationality}"'))
def search_by_nationality(engine, context, nationality):
    context["result"] = engine.search_players(nationality=nationality)


@when(parsers.parse('I search players at club "{club}"'))
def search_by_club(engine, context, club):
    context["result"] = engine.search_players(club=club)


@when(parsers.parse('I request the top {limit:d} players with nationality "{nationality}"'))
def top_by_nationality(engine, context, limit, nationality):
    context["result"] = engine.top_players(nationality=nationality, limit=limit)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then("I should find at least one player")
def check_players_found(context):
    assert context["result"]["total"] > 0
    assert context["result"]["players"]


@then("each player should have name, club, position and rating")
def check_player_fields(context):
    for player in context["result"]["players"]:
        assert player["Name"]
        assert player["Club"]
        assert player["Position"]
        assert isinstance(player["Overall"], int)


@then(parsers.parse('all returned players should have nationality "{nationality}"'))
def check_nationality(context, nationality):
    for player in context["result"]["players"]:
        assert player["Nationality"] == nationality


@then(parsers.parse('all returned players should play for a club containing "{club}"'))
def check_club(context, club):
    for player in context["result"]["players"]:
        assert club.lower() in player["Club"].lower()


@then(parsers.parse("I should receive exactly {count:d} players"))
def check_player_count(context, count):
    assert len(context["result"]["players"]) == count


@then("the players should be sorted by overall rating descending")
def check_sorted(context):
    ratings = [p["Overall"] for p in context["result"]["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then(parsers.parse("the best player should have an overall rating of at least {rating:d}"))
def check_best_rating(context, rating):
    best = context["result"]["players"][0]
    assert best["Overall"] >= rating
