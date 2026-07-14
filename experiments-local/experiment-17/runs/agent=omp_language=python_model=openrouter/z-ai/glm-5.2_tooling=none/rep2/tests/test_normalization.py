"""BDD step definitions for team-name normalisation scenarios."""

from __future__ import annotations

from pytest_bdd import scenarios, when, then, parsers

scenarios("features/normalization.feature")


@when(parsers.parse('I resolve the team name "{name}"'))
def resolve_one(data, ctx, name):
    ctx["id"] = data.resolve_team(name)


@when(parsers.parse('I resolve the team names "{a}" and "{b}"'))
def resolve_two(data, ctx, a, b):
    ctx["id_a"] = data.resolve_team(a)
    ctx["id_b"] = data.resolve_team(b)


@then(parsers.parse('the canonical id should be "{id}"'))
def assert_id(ctx, id):
    assert ctx["id"] == id, (ctx["id"], id)


@then("their canonical ids should differ")
def assert_differ(ctx):
    assert ctx["id_a"] != ctx["id_b"], (ctx["id_a"], ctx["id_b"])
