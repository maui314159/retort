"""BDD steps for performance.feature."""

from __future__ import annotations

import time

from pytest_bdd import parsers, scenarios, then, when

from conftest import _parse_args

scenarios("features/performance.feature")


@when(parsers.parse('I time a call to "{tool}" with arguments "{raw_args}"'))
def timed_call(server, ctx, tool, raw_args):
    start = time.perf_counter()
    import asyncio

    result = asyncio.run(server.call_tool(tool, _parse_args(raw_args)))
    ctx["elapsed"] = time.perf_counter() - start
    ctx["tool_result"] = result.content[0].text if result.content else ""
    assert ctx["tool_result"], "tool produced no output"


@then(parsers.parse("the call should take less than {seconds:d} seconds"))
def under_seconds(ctx, seconds):
    assert ctx["elapsed"] < seconds, f"took {ctx['elapsed']:.2f}s (limit {seconds}s)"


@then("the dataset should contain more than 15000 matches")
def dataset_size(dataset):
    assert len(dataset.matches) > 15000
