"""BDD step definitions for the Team Name Normalization feature."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/normalization.feature")


@given("the match data is loaded")
def match_data_loaded(kg):
    assert kg is not None


@when('I normalize the team name "<spelling>"', target_fixture="result")
def normalize_spelling(kg, context, spelling):
    res = kg.dataset.normalizer.canonical(spelling)
    context["result"] = res
    context["spelling"] = spelling
    return res


@when(
    'I normalize the team names "{a}" and "{b}"',
    target_fixture="result",
)
def normalize_pair(kg, context, a, b):
    res = {"a": kg.dataset.normalizer.canonical(a), "b": kg.dataset.normalizer.canonical(b)}
    context["result"] = res
    return res


@then('the canonical name should be "<canonical>"')
def canonical_equals(context, canonical):
    assert context["result"] == canonical, (
        f"{context['spelling']!r} -> {context['result']!r}, expected {canonical!r}"
    )


@then("they should resolve to different canonical clubs")
def pair_distinct(context):
    res = context["result"]
    assert res["a"] is not None and res["b"] is not None
    assert res["a"] != res["b"], f"both resolved to {res['a']!r}"
