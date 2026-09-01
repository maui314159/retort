"""Feature: MCP Protocol
  The server must speak the Model Context Protocol over stdio: initialize
  handshake, tools/list, tools/call (including error results), resources,
  ping, and proper JSON-RPC error codes for malformed traffic.

  The suite exercises the server end-to-end through a real subprocess and
  additionally drives the protocol handler in-process to cover every
  dispatch branch directly.
"""

import io
import json

import pytest

from brazilian_soccer.protocol import MCPStdioServer
from brazilian_soccer.tools import build_tool_registry


class TestInitialize:
    def test_initialize_handshake(self, mcp):
        # Given a fresh server process (already initialized in the fixture)
        # When the client re-initializes
        response = mcp.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0.0.0"},
            },
        )
        # Then the server echoes a supported protocol version and identifies itself
        result = response["result"]
        assert result["protocolVersion"] == "2025-03-26"
        assert result["serverInfo"]["name"] == "brazilian-soccer-mcp"
        assert result["serverInfo"]["version"]
        assert "tools" in result["capabilities"]

    def test_initialize_echoes_known_version_and_defaults_otherwise(self, mcp):
        # Given an unknown protocol version request
        response = mcp.request(
            "initialize",
            {
                "protocolVersion": "1999-01-01",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        )
        # Then the server falls back to a version it supports
        assert response["result"]["protocolVersion"] == "2024-11-05"

    def test_ping(self, mcp):
        response = mcp.request("ping")
        assert response["result"] == {}


class TestTools:
    def test_tools_list_exposes_twelve_tools_with_schemas(self, mcp):
        # Given the running server
        response = mcp.request("tools/list")
        tools = response["result"]["tools"]
        names = {tool["name"] for tool in tools}
        # When tools are listed
        # Then all capability areas from the specification are covered
        assert names == {
            "search_matches",
            "head_to_head",
            "team_stats",
            "team_rankings",
            "find_team",
            "search_players",
            "player_detail",
            "standings",
            "competition_info",
            "biggest_wins",
            "stats_summary",
            "derby_matches",
        }
        for tool in tools:
            assert tool["description"]
            assert tool["inputSchema"]["type"] == "object"

    def test_tools_call_returns_json_text_content(self, mcp):
        # Given a tools/call request
        result = mcp.call_tool(
            "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}
        )
        # When executed
        # Then the result is JSON with the head-to-head totals
        assert result["matches_played"] == 44
        assert result["team_a"] == "Flamengo"

    def test_tools_call_ambiguous_team_returns_is_error(self, mcp):
        # Given an ambiguous team name
        response = mcp.request(
            "tools/call", {"name": "team_stats", "arguments": {"team": "America"}}
        )
        # When the tool runs
        # Then the result is a tool-level error, not a protocol error
        result = response["result"]
        assert result["isError"] is True
        assert "America MG" in result["content"][0]["text"]

    def test_unknown_tool_returns_invalid_params(self, mcp):
        response = mcp.request("tools/call", {"name": "nonsense", "arguments": {}})
        assert response["error"]["code"] == -32602

    def test_every_tool_is_callable_end_to_end(self, mcp):
        # Given one representative call per tool
        calls = {
            "search_matches": {"team": "Flamengo", "limit": 3},
            "head_to_head": {"team_a": "Palmeiras", "team_b": "Santos"},
            "team_stats": {"team": "Corinthians", "season": 2019},
            "team_rankings": {"metric": "away_points", "limit": 3},
            "find_team": {"query": "Grêmio"},
            "search_players": {"nationality": "Brazil", "limit": 3},
            "player_detail": {"name": "Neymar Jr"},
            "standings": {"competition": "brasileirao", "season": 2019},
            "competition_info": {},
            "biggest_wins": {"limit": 3},
            "stats_summary": {"competition": "serie a"},
            "derby_matches": {"season": 2023},
        }
        # When each tool is called through the protocol
        # Then every call returns structured JSON content
        for name, arguments in calls.items():
            result = mcp.call_tool(name, arguments)
            assert isinstance(result, dict), name


class TestResources:
    def test_resources_list(self, mcp):
        response = mcp.request("resources/list")
        uris = {resource["uri"] for resource in response["result"]["resources"]}
        # When resources are listed
        # Then all six datasets plus a competitions overview are exposed
        assert len(uris) == 7
        assert "soccer://competitions" in uris
        assert "soccer://datasets/fifa_data" in uris

    def test_resources_read(self, mcp):
        response = mcp.request(
            "resources/read", {"uri": "soccer://datasets/brasileirao_matches"}
        )
        content = response["result"]["contents"][0]
        # When a dataset resource is read
        # Then a JSON summary with loaded row counts is returned
        assert content["mimeType"] == "application/json"
        body = json.loads(content["text"])
        assert body["file"] == "Brasileirao_Matches.csv"
        assert body["rows"] == 4180

    def test_unknown_resource_returns_invalid_params(self, mcp):
        response = mcp.request("resources/read", {"uri": "soccer://nope"})
        assert response["error"]["code"] == -32602

    def test_prompts_list_is_empty(self, mcp):
        response = mcp.request("prompts/list")
        assert response["result"] == {"prompts": []}


class TestProtocolErrors:
    def test_malformed_json_line_returns_parse_error(self, mcp):
        # Given a line that is not JSON
        mcp.process.stdin.write("this is not json\n")
        mcp.process.stdin.flush()
        # When the server processes it
        # Then it answers with a JSON-RPC parse error and keeps running
        response = mcp.read()
        assert response["error"]["code"] == -32700
        pong = mcp.request("ping")
        assert pong["result"] == {}

    def test_unknown_method_returns_method_not_found(self, mcp):
        response = mcp.request("resources/subscribe")
        assert response["error"]["code"] == -32601

    def test_notifications_produce_no_response(self, mcp):
        # Given a notification (no id)
        mcp.notify("notifications/initialized")
        mcp.notify("$/cancelled", {"requestId": 1})
        # When followed by a request
        pong = mcp.request("ping")
        # Then the very next message answers the request, not the notifications
        assert pong["result"] == {}


class TestInProcessServer:
    """Drive the protocol handler directly (covers every dispatch branch)."""

    @pytest.fixture()
    def server(self, repo) -> MCPStdioServer:
        from brazilian_soccer.protocol import build_dataset_resources

        return MCPStdioServer(
            server_name="test-server",
            server_version="0.1.0",
            tools=build_tool_registry(repo),
            resources=build_dataset_resources(repo),
        )

    def _exchange(self, server: MCPStdioServer, message) -> dict | None:
        stream = io.StringIO()
        server._handle(message, stream)
        raw = stream.getvalue()
        return json.loads(raw) if raw.strip() else None

    def test_dispatch_covers_core_methods(self, server):
        # Given requests for every core method
        # When handled one by one
        # Then each returns a proper result
        init = self._exchange(
            server,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert init["result"]["serverInfo"]["name"] == "test-server"
        assert self._exchange(server, {"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}
        tools = self._exchange(server, {"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert len(tools["result"]["tools"]) == 12
        call = self._exchange(
            server,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "standings", "arguments": {"competition": "serie a", "season": 2019}},
            },
        )
        assert json.loads(call["result"]["content"][0]["text"])["champion"] == "Flamengo"
        resources = self._exchange(server, {"jsonrpc": "2.0", "id": 5, "method": "resources/list"})
        assert len(resources["result"]["resources"]) == 7

    def test_notification_is_ignored_silently(self, server):
        # Given a notification without an id
        # When handled
        # Then nothing is written to the output stream
        assert self._exchange(server, {"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    def test_invalid_request_shape(self, server):
        response = self._exchange(server, {"jsonrpc": "2.0", "id": 9})
        assert response["error"]["code"] == -32600

    def test_tool_crash_becomes_internal_error(self, server):
        # Given a tool whose handler raises unexpectedly
        server.tools.append(
            {
                "name": "boom",
                "description": "explodes",
                "inputSchema": {"type": "object", "properties": {}},
                "handler": lambda args: 1 / 0,
            }
        )
        # When called
        response = self._exchange(
            server,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "boom", "arguments": {}}},
        )
        # Then a JSON-RPC internal error is returned, not a crash
        assert response["error"]["code"] == -32603

    def test_run_loop_processes_a_batch_of_messages(self, server):
        # Given a stream with several newline-delimited messages
        stream_in = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
            + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
        )
        stream_out = io.StringIO()
        # When the run loop consumes it
        server.run(stream_in, stream_out)
        # Then every request was answered
        lines = [json.loads(line) for line in stream_out.getvalue().splitlines()]
        assert [line["id"] for line in lines] == [1, 2]
