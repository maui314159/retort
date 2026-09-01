"""
soccer_mcp.bdd -- a tiny Given/When/Then harness for BDD-style pytest.

CONTEXT
-------
The specification (TASK.md, "Testing Approach") requires BDD test scenarios:

    Feature: Match Queries
    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition

Rather than pulling in pytest-bdd (Gherkin parsing, fixtures indirection),
this module provides a fluent ``Scenario`` object whose steps execute in
order and whose failures re-raise as AssertionError with the full
feature/scenario/step context attached.  The test files read like the
Gherkin scenarios while remaining plain pytest functions.

Example:
    def test_find_matches_between_two_teams():
        (
            Scenario("Match Queries", "Find matches between two teams")
            .given("the match data is loaded", dataset=dataset)
            .when("I search for matches between 'Flamengo' and 'Fluminense'",
                  result=lambda ctx: search_matches(ctx["dataset"], ...))
            .then("I should receive a list of matches",
                  lambda ctx: expect(len(ctx["result"]) > 0))
            .run()
        )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _Step:
    kind: str  # "Given" | "When" | "Then" | "And"
    description: str
    action: Callable[[dict], Any] | None = None
    stores: str | None = None


class Scenario:
    """One BDD scenario: ordered Given/When/Then steps over a shared context."""

    def __init__(self, feature: str, name: str) -> None:
        self.feature = feature
        self.name = name
        self.context: dict[str, Any] = {}
        self._steps: list[_Step] = []
        self._last_kind: str | None = None

    # -- fluent step builders ---------------------------------------------------

    def given(self, description: str, **facts: Any) -> "Scenario":
        """Register facts into the scenario context."""
        self._steps.append(_Step("Given", description, stores=None))
        self._steps[-1].action = lambda ctx, facts=facts: ctx.update(facts)
        self._last_kind = "Given"
        return self

    def when(self, description: str, **actions: Callable[[dict], Any]) -> "Scenario":
        """Register actions: each callable receives the context and its
        return value is stored under the keyword name."""
        for key, action in actions.items():
            self._steps.append(_Step("When" if key == list(actions)[0] else "And",
                                     description, action=action, stores=key))
        self._last_kind = "When"
        return self

    def then(self, description: str, assertion: Callable[[dict], Any] | None = None,
             **expectations: Any) -> "Scenario":
        """Register assertions.  Either a single callable, or expected values
        for context keys (compared with ``==``)."""
        if assertion is not None:
            self._steps.append(_Step("Then", description, action=assertion))
        for key, expected in expectations.items():
            def check(ctx: dict, key=key, expected=expected) -> None:
                actual = ctx.get(key, _MISSING)
                if actual is _MISSING:
                    raise AssertionError(f"context has no key '{key}'")
                if actual != expected:
                    raise AssertionError(
                        f"expected {key} == {expected!r}, got {actual!r}"
                    )
            self._steps.append(_Step("Then", description, action=check))
        self._last_kind = "Then"
        return self

    def and_(self, description: str, assertion: Callable[[dict], Any] | None = None,
             **actions: Callable[[dict], Any]) -> "Scenario":
        """An additional clause.

        With a positional callable it is a Then-style assertion; with keyword
        callables it is a When-style action storing each result.
        """
        if assertion is not None:
            self._steps.append(_Step("And", description, action=assertion))
        for key, action in actions.items():
            self._steps.append(_Step("And", description, action=action, stores=key))
        return self

    # -- execution ---------------------------------------------------------------

    def run(self) -> None:
        """Execute all steps in order.

        Failures raise AssertionError carrying the scenario trace.  ``Given``
        step errors abort the scenario; ``When`` step errors are captured in
        the context as ``error`` (so Then steps can assert on them); ``Then``
        step errors fail the test.
        """
        executed: list[str] = []
        for step in self._steps:
            label = f"{step.kind} {step.description}"
            try:
                if step.action is None:
                    continue
                outcome = step.action(self.context)
                if step.stores:
                    self.context[step.stores] = outcome
            except AssertionError:
                raise AssertionError(self._trace(executed, label)) from None
            except Exception as error:  # noqa: BLE001
                if step.kind in {"When", "And"} and step.stores:
                    # capture query errors so Thens can inspect them
                    self.context[step.stores] = None
                    self.context["error"] = error
                else:
                    raise AssertionError(
                        self._trace(executed, label, cause=error)
                    ) from error
            executed.append(label)

    def _trace(self, executed: list[str], failing: str, cause: Exception | None = None) -> str:
        lines = [f"BDD failure in scenario: {self.name}", f"Feature: {self.feature}"]
        for label in executed:
            lines.append(f"  OK   {label}")
        lines.append(f"  FAIL {failing}")
        if cause is not None:
            lines.append(f"  caused by: {type(cause).__name__}: {cause}")
        return "\n".join(lines)


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover
        return "<missing>"


_MISSING = _Missing()


# ---------------------------------------------------------------------------
# Assertion helpers -- each returns None on success, raises AssertionError
# ---------------------------------------------------------------------------


def expect(condition: Any, message: str = "condition was false") -> None:
    if not condition:
        raise AssertionError(message)


def expect_equal(actual: Any, expected: Any, message: str = "") -> None:
    if actual != expected:
        raise AssertionError(message or f"expected {expected!r}, got {actual!r}")


def expect_contains(container: Any, item: Any, message: str = "") -> None:
    if item not in container:
        raise AssertionError(message or f"{item!r} not found in container")


def expect_gt(actual: Any, threshold: Any, message: str = "") -> None:
    if not actual > threshold:
        raise AssertionError(message or f"expected {actual!r} > {threshold!r}")


def expect_gte(actual: Any, threshold: Any, message: str = "") -> None:
    if not actual >= threshold:
        raise AssertionError(message or f"expected {actual!r} >= {threshold!r}")


def expect_lt(actual: Any, threshold: Any, message: str = "") -> None:
    if not actual < threshold:
        raise AssertionError(message or f"expected {actual!r} < {threshold!r}")


def expect_in_range(actual: Any, low: Any, high: Any, message: str = "") -> None:
    if not low <= actual <= high:
        raise AssertionError(message or f"expected {low!r} <= {actual!r} <= {high!r}")


def expect_none(actual: Any, message: str = "") -> None:
    if actual is not None:
        raise AssertionError(message or f"expected None, got {actual!r}")


def expect_not_none(actual: Any, message: str = "") -> None:
    if actual is None:
        raise AssertionError(message or "expected a value, got None")
