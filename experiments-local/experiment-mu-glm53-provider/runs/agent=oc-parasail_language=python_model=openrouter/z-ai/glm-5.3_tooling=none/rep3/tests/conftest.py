"""Shared fixtures and BDD step definitions for the Brazilian soccer tests.

The heavy fixtures (dataset, MCP server) are session-scoped so the CSVs
are parsed once for the whole test run.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import pytest

# Make the repository root importable regardless of where pytest runs from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brazilian_soccer.loader import SoccerData, load_soccer_data  # noqa: E402


def run_async(coro):
    """Run a coroutine to completion (each BDD step gets a fresh loop)."""
    return asyncio.run(coro)


@pytest.fixture(scope="session")
def soccer_data() -> SoccerData:
    return load_soccer_data()


@pytest.fixture(scope="session")
def mcp_server():
    import server as server_module

    return server_module.build_server()


@pytest.fixture
def ctx():
    """Per-scenario scratch space shared between Given/When/Then steps."""
    return {}


# ---------------------------------------------------------------------------
# Shared BDD steps
# ---------------------------------------------------------------------------

from pytest_bdd import given, parsers, then, when  # noqa: E402


@given("the match data is loaded", target_fixture="dataset")
def match_data_loaded(soccer_data):
    return soccer_data


@given("the player data is loaded", target_fixture="dataset")
def player_data_loaded(soccer_data):
    return soccer_data


@given("the MCP server is running", target_fixture="server")
def mcp_server_running(mcp_server):
    return mcp_server


def _parse_args(raw: str) -> dict:
    """Parse a 'key=value, key=value' mini-DSL into tool arguments."""
    args = {}
    for part in re.split(r"[,;]", raw):
        part = part.strip()
        if not part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if re.fullmatch(r"-?\d+", value):
            args[key] = int(value)
        elif value.lower() in {"true", "false"}:
            args[key] = value.lower() == "true"
        else:
            args[key] = value
    return args


@when(parsers.parse('I call the MCP tool "{tool}" with arguments "{raw_args}"'))
def call_mcp_tool(server, ctx, tool, raw_args):
    result = run_async(server.call_tool(tool, _parse_args(raw_args)))
    ctx["tool_result"] = result.content[0].text if result.content else ""
    ctx["tool_error"] = getattr(result, "isError", False)
    return ctx["tool_result"]


@when(parsers.parse('I call the MCP tool "{tool}"'))
def call_mcp_tool_no_args(server, ctx, tool):
    return call_mcp_tool.__wrapped__(server, ctx, tool, "")


@then(parsers.parse('the response should contain "{text}"'))
def response_contains(ctx, text):
    assert ctx["tool_result"], "tool returned an empty response"
    assert text in ctx["tool_result"], (
        f"Expected {text!r} in response:\n{ctx['tool_result'][:500]}"
    )


@then(parsers.parse('the response should not contain "{text}"'))
def response_not_contains(ctx, text):
    assert text not in ctx["tool_result"]
