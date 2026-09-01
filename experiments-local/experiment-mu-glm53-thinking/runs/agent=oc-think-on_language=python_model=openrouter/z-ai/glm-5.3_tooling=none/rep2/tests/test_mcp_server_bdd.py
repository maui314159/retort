"""BDD scenarios for the MCP server layer.

Feature: MCP server
  The knowledge base is exposed as an MCP server: every capability is
  registered as a tool, tools answer through the MCP call machinery, and
  the server speaks the MCP stdio protocol end-to-end.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys

EXPECTED_TOOLS = {
    "search_matches",
    "head_to_head",
    "last_meeting",
    "find_finals",
    "derbies",
    "team_record",
    "team_profile",
    "list_teams",
    "best_records",
    "search_players",
    "top_players",
    "club_squad",
    "brazilian_players_by_club",
    "competition_info",
    "standings",
    "stats_summary",
    "biggest_wins",
    "season_comparison",
}


def _call(server, name, arguments):
    return asyncio.run(server.call_tool(name, arguments))


def _payload(result):
    return json.loads(result.content[0].text)


def test_all_tools_are_registered(server):
    """Scenario: Tool catalogue
    Given the MCP server is built
    When the client lists tools
    Then all 18 tools are registered with descriptions
    """
    # Given / When
    tools = asyncio.run(server.list_tools())

    # Then
    names = {tool.name for tool in tools}
    assert names == EXPECTED_TOOLS
    assert len(tools) == 18
    assert all(tool.description for tool in tools)


def test_tool_schema_requires_mandatory_arguments(server):
    """Scenario: Tool schemas
    Given the head_to_head tool needs two teams
    When its input schema is inspected
    Then team_a and team_b are required strings
    """
    # Given / When
    tools = asyncio.run(server.list_tools())
    schema = next(t for t in tools if t.name == "head_to_head").input_schema

    # Then
    assert set(schema["required"]) == {"team_a", "team_b"}
    assert schema["properties"]["team_a"]["type"] == "string"


def test_calling_a_match_tool(server):
    """Scenario: Calling a match tool over MCP
    Given a connected MCP client
    When the head_to_head tool is called for Fla-Flu
    Then the structured answer comes back through the protocol
    """
    # Given / When
    result = _call(server, "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"})

    # Then
    assert not result.is_error
    payload = _payload(result)
    assert payload["team_a"] == "Flamengo"
    assert payload["total_matches"] == 44
    assert payload["team_a_wins"] == 18


def test_calling_a_competition_tool(server):
    """Scenario: Calling the standings tool over MCP
    Given a connected MCP client
    When the standings tool is called for the 2019 Série A
    Then Flamengo is returned as champion
    """
    # Given / When
    result = _call(
        server, "standings", {"competition": "Brasileirão Série A", "season": 2019}
    )

    # Then
    payload = _payload(result)
    assert payload["champion"] == "Flamengo"
    assert payload["table"][0]["points"] == 90


def test_calling_a_player_tool(server):
    """Scenario: Calling a player tool over MCP
    Given a connected MCP client
    When search_players is called for "Neymar"
    Then his FIFA profile is returned
    """
    # Given / When
    result = _call(server, "search_players", {"name": "Neymar"})

    # Then
    payload = _payload(result)
    assert payload["total"] == 1
    assert payload["players"][0]["name"] == "Neymar Jr"
    assert payload["players"][0]["overall"] == 92


def test_team_name_variants_over_mcp(server):
    """Scenario: Name variants through the protocol
    Given a client sends "Corinthians-SP"
    When the team_record tool is called
    Then the club resolves to Corinthians
    """
    # Given / When
    result = _call(
        server,
        "team_record",
        {"team": "Corinthians-SP", "season": 2019, "competition": "Brasileirão Série A"},
    )

    # Then
    payload = _payload(result)
    assert payload["team"] == "Corinthians"
    assert payload["matches"] == 38


def test_unknown_tool_raises_tool_error(server):
    """Scenario: Unknown tool
    Given a client calls a tool that does not exist
    When the call is made
    Then a ToolError is raised
    """
    # Given
    from mcp.server.mcpserver.exceptions import ToolError

    # When / Then
    try:
        _call(server, "time_travel", {})
    except ToolError as error:
        assert "Unknown tool" in str(error)
    else:
        raise AssertionError("expected ToolError")


def test_bad_argument_raises_error(server):
    """Scenario: Invalid tool arguments
    Given a client asks for a team that does not exist
    When the tool runs
    Then the failure surfaces as a tool error
    """
    # Given
    from mcp.server.mcpserver.exceptions import UnexpectedToolError

    # When / Then
    try:
        _call(server, "team_record", {"team": "Hogwarts School FC"})
    except UnexpectedToolError:
        pass
    else:
        raise AssertionError("expected UnexpectedToolError")


def test_stdio_round_trip():
    """Scenario: The server runs as a real MCP stdio server
    Given the server is launched with `python -m brazilian_soccer_mcp`
    When a client initialises, lists tools and calls one
    Then valid JSON-RPC responses come back over stdio
    """
    # Given
    proc = subprocess.Popen(
        [sys.executable, "-m", "brazilian_soccer_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # When
        request = proc.stdin.write
        request(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "bdd-test", "version": "1.0"},
                    },
                }
            )
            + "\n"
        )
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n")
        proc.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "standings",
                        "arguments": {
                            "competition": "Brasileirão Série A",
                            "season": 2019,
                        },
                    },
                }
            )
            + "\n"
        )
        proc.stdin.flush()

        initialize = json.loads(proc.stdout.readline())
        tool_list = json.loads(proc.stdout.readline())
        tool_call = json.loads(proc.stdout.readline())

        # Then
        assert initialize["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"
        assert {t["name"] for t in tool_list["result"]["tools"]} == EXPECTED_TOOLS
        text = tool_call["result"]["content"][0]["text"]
        payload = json.loads(text)
        assert payload["champion"] == "Flamengo"
    finally:
        proc.terminate()
        proc.wait(timeout=10)
