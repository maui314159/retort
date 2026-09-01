"""
BDD (Given/When/Then) scenarios for the MCP server tool layer.

Context block
=============
Purpose: validate that every MCP tool declared by ``mcp_server`` is
discoverable, has a valid schema, and dispatches to the query engine
returning JSON-serializable results. Also exercises the data-loading
contract that all six CSV files are loaded and queryable.
"""

from __future__ import annotations

import json

from brazilian_soccer_mcp import mcp_server as mcp_server_mod


# ---------------------------------------------------------------------------
# Feature: MCP Tool Discovery & Dispatch
# ---------------------------------------------------------------------------


def test_all_six_csv_files_loaded(engine):
    """Scenario: Data coverage.

    Given the six CSV files under data/kaggle/
    When the data loader runs
    Then matches and players should be populated
    And the matches should span multiple competitions
    """
    assert len(engine.loader.matches) > 20000
    assert len(engine.loader.players) > 18000
    competitions = {m.competition for m in engine.loader.matches}
    assert "Brasileirao" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions


def test_tool_list_is_non_empty():
    """Scenario: Tools are declared.

    Given the MCP server module
    When I inspect the TOOLS list
    Then there should be at least 15 tools
    And each tool should have a name, description and input schema
    """
    assert len(mcp_server_mod.TOOLS) >= 15
    for tool in mcp_server_mod.TOOLS:
        assert tool.name
        assert tool.description
        assert tool.input_schema["type"] == "object"


def test_find_matches_tool_dispatches():
    """Scenario: find_matches tool returns JSON.

    Given the MCP server tool layer
    When I call the find_matches tool with team=Flamengo
    Then I should receive a JSON-serializable list of matches
    """
    result = mcp_server_mod.dispatch_tool("find_matches", {"team": "Flamengo", "limit": 5})
    assert isinstance(result, list)
    assert len(result) > 0
    json.dumps(result)  # must be JSON-serializable


def test_champion_tool_dispatches():
    """Scenario: champion tool returns the champion.

    Given the MCP server tool layer
    When I call the champion tool for Brasileirao 2019
    Then I should receive Flamengo as champion
    """
    result = mcp_server_mod.dispatch_tool("champion", {"competition": "Brasileirao", "season": "2019"})
    assert result["champion"] == "Flamengo"


def test_unknown_tool_raises():
    """Scenario: Unknown tool is rejected.

    Given the MCP server tool layer
    When I call a non-existent tool
    Then a ValueError should be raised
    """
    try:
        mcp_server_mod.dispatch_tool("does_not_exist", {})
    except ValueError:
        return
    raise AssertionError("Expected ValueError for unknown tool")


def test_head_to_head_tool_dispatches():
    """Scenario: head_to_head tool returns aggregate record.

    Given the MCP server tool layer
    When I call head_to_head for Flamengo vs Fluminense
    Then the result should include wins, draws and a match list
    """
    result = mcp_server_mod.dispatch_tool(
        "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}
    )
    assert result["matches"] > 0
    assert "team_a_wins" in result
    assert "team_b_wins" in result
    assert "draws" in result
