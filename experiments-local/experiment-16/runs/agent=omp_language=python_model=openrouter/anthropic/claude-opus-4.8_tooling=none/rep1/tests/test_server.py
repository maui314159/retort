"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_server
Purpose : Exercise the MCP tool layer end-to-end through the FastMCP server,
          injecting the sample graph so the registered tools return the same
          structured payloads an MCP client would receive. Verifies tool
          registration and that each tool round-trips through call_tool.
================================================================================
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer import server


@pytest.fixture(autouse=True)
def _inject(sample_graph):
    server.set_graph(sample_graph)
    yield
    server.set_graph(None)


def _payload(result):
    """Extract the dict/text payload from a FastMCP call_tool result."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    # Older/newer shapes: (content, structured) tuple or content list.
    if isinstance(result, tuple):
        content, structured = result
        if structured is not None:
            return structured
        result = content
    block = result[0]
    text = getattr(block, "text", block)
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


@pytest.mark.asyncio
async def test_tools_are_registered():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    assert {
        "search_matches",
        "head_to_head",
        "team_record",
        "search_players",
        "standings",
        "average_goals",
        "biggest_wins",
        "best_records",
        "answer",
    } <= names


@pytest.mark.asyncio
async def test_search_matches_tool():
    res = await server.mcp.call_tool(
        "search_matches", {"team": "Flamengo", "opponent": "Fluminense"}
    )
    data = _payload(res)
    assert data["count"] == 2


@pytest.mark.asyncio
async def test_head_to_head_tool():
    res = await server.mcp.call_tool(
        "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}
    )
    data = _payload(res)
    assert data["team_a_wins"] == 1
    assert data["team_b_wins"] == 1


@pytest.mark.asyncio
async def test_standings_tool():
    res = await server.mcp.call_tool(
        "standings", {"competition": "Brasileirão", "season": 2023}
    )
    data = _payload(res)
    pts = [row["points"] for row in data["table"]]
    assert pts == sorted(pts, reverse=True)


@pytest.mark.asyncio
async def test_search_players_tool():
    res = await server.mcp.call_tool(
        "search_players", {"nationality": "Brazil"}
    )
    data = _payload(res)
    assert data["count"] >= 1
    assert all(p["nationality"] == "Brazil" for p in data["players"])


@pytest.mark.asyncio
async def test_answer_who_is():
    res = await server.mcp.call_tool("answer", {"question": "Who is Gabriel Barbosa?"})
    text = _payload(res)
    if isinstance(text, dict):  # some versions wrap str returns
        text = text.get("result", str(text))
    assert "Gabriel Barbosa" in str(text)
