"""Step definitions for player_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe

scenarios("features/player_queries.feature")

FORWARD_POSITIONS = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}


@when(parsers.parse('I search for a player named "{name}"'))
def search_by_name(store, context, name):
    context["result"] = qe.search_players(name=name, store=store)


@when(parsers.parse('I search for players with nationality "{nationality}"'))
def search_by_nationality(store, context, nationality):
    context["result"] = qe.search_players(nationality=nationality, limit=100,
                                          store=store)


@when(parsers.parse('I request the top {limit:d} players with nationality '
                    '"{nationality}"'))
def top_by_nationality(store, context, limit, nationality):
    context["result"] = qe.top_players(nationality=nationality, limit=limit,
                                       store=store)


@when(parsers.parse('I search for forwards at club "{club}"'))
def search_forwards(store, context, club):
    context["result"] = qe.search_players(club=club, position="forward",
                                          limit=100, store=store)


@when(parsers.parse('I request the profile of "{name}"'))
def profile(store, context, name):
    context["result"] = qe.player_profile(name, store=store)


@then(parsers.parse("I should find exactly {count:d} player"))
@then(parsers.parse("I should find exactly {count:d} players"))
def check_exact_count(context, count):
    assert context["result"]["total"] == count


@then(parsers.parse("I should find more than {count:d} players"))
def check_more_than(context, count):
    assert context["result"]["total"] > count


@then(parsers.parse("I should find at least {count:d} players"))
def check_at_least(context, count):
    assert context["result"]["total"] >= count


@then(parsers.parse('the player should be "{name}" with overall {overall:d}'))
def check_player_identity(context, name, overall):
    player = context["result"]["players"][0]
    assert player["name"] == name
    assert player["overall"] == overall


@then(parsers.parse('every player should have nationality "{nationality}"'))
def check_nationality(context, nationality):
    for player in context["result"]["players"]:
        assert player["nationality"] == nationality


@then(parsers.parse('every player club should contain "{club}"'))
def check_club(context, club):
    for player in context["result"]["players"]:
        assert club in player["club"]


@then(parsers.parse("I should receive {count:d} players"))
def check_received(context, count):
    assert context["result"]["returned"] == count
    assert len(context["result"]["players"]) == count


@then("the players should be sorted by descending overall rating")
def check_sorted(context):
    ratings = [p["overall"] for p in context["result"]["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then(parsers.parse('the first player should be "{name}"'))
def check_first(context, name):
    assert context["result"]["players"][0]["name"] == name


@then("every player position should be a forward position")
def check_forward(context):
    assert context["result"]["total"] > 0
    for player in context["result"]["players"]:
        assert player["position"] in FORWARD_POSITIONS


@then("the profile should be found")
def check_profile_found(context):
    assert context["result"]["found"] is True


@then("the profile should not be found")
def check_profile_not_found(context):
    assert context["result"]["found"] is False


@then(parsers.parse('the player should play for "{club}"'))
def check_profile_club(context, club):
    assert context["result"]["player"]["club"] == club


@then("the profile should include skill ratings")
def check_skills(context):
    skills = context["result"]["player"]["skills"]
    assert len(skills) > 5
    assert all(isinstance(v, int) for v in skills.values())
