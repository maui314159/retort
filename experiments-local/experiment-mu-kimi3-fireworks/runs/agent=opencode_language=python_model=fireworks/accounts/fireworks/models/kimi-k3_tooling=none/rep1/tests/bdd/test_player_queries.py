"""BDD step definitions for player_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from soccer_mcp import queries as q

scenarios("../features/player_queries.feature")


@when(parsers.parse('I search for a player named "{name}"'))
def search_by_name(store, context, name):
    context["result"] = q.search_players(store, name=name)


@when(parsers.parse('I filter players by nationality "{nationality}"'))
def filter_nationality(store, context, nationality):
    context["result"] = q.search_players(store, nationality=nationality, limit=1000)


@when(parsers.parse('I filter players by club "{club}"'))
def filter_club(store, context, club):
    context["result"] = q.search_players(store, club=club, limit=200)


@when(parsers.parse('I filter "{club}" players by position group "{group}"'))
def filter_club_group(store, context, club, group):
    context["result"] = q.search_players(store, club=club,
                                         position_group=group, limit=200)


@when(parsers.parse("I ask for the top {limit:d} Brazilian players by rating"))
def top_brazilian(store, context, limit):
    context["result"] = q.top_players(store, nationality="Brazil", limit=limit)


@when(parsers.parse('I ask for the profile of "{name}"'))
def profile(store, context, name):
    context["profile"] = q.player_profile(store, name)
    context["text"] = str(context["profile"])


@then(parsers.parse('the top result should be "{name}"'))
def top_result_is(context, name):
    assert context["result"]["players"][0]["name"] == name


@then(parsers.parse("I should find more than {count:d} players"))
def more_than_players(context, count):
    assert context["result"]["total"] > count


@then("every player should be Brazilian")
def all_brazilian(context):
    for p in context["result"]["players"]:
        assert p["nationality"] == "Brazil"


@then(parsers.parse('the first player should be "{name}" with rating {rating:d}'))
def first_player_rating(context, name, rating):
    top = context["result"]["players"][0]
    assert top["name"] == name
    assert top["overall"] == rating


@then("the players should be sorted by overall rating")
def sorted_by_overall(context):
    ratings = [p["overall"] for p in context["result"]["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then(parsers.parse('every player should play for "{club}"'))
def all_at_club(context, club):
    assert context["result"]["players"]
    for p in context["result"]["players"]:
        assert p["club"] == club


@then(parsers.parse("I should receive at least {count:d} players"))
def at_least_players(context, count):
    assert context["result"]["total"] >= count


@then("every player should be a forward")
def all_forwards(context):
    for p in context["result"]["players"]:
        assert p["position_group"] == "forward"


@then(parsers.parse('the profile should show club "{club}"'))
def profile_club(context, club):
    assert context["profile"]["club"] == club


@then("the profile should include skill ratings")
def profile_skills(context):
    assert context["profile"]["skills"]
