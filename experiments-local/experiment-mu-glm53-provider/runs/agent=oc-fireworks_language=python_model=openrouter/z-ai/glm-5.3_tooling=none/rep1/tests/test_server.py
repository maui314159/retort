"""
Feature: The MCP server protocol
  The server speaks Model Context Protocol over stdio: newline-delimited
  JSON-RPC 2.0.  These scenarios verify the handshake, tool listing, tool
  calls (including error semantics), resources, error codes and a full
  end-to-end session over real pipes.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from brazilian_soccer_mcp.loader import load_dataset
from brazilian_soccer_mcp.server import MCPServer
from brazilian_soccer_mcp.tools import TOOL_NAMES, tool_summaries

# --------------------------------------------------------------------------
# Unit level: drive the handler with decoded messages
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def server() -> MCPServer:
    """A server wired to the real dataset, initialised once for this module."""
    srv = MCPServer(dataset=load_dataset())
    srv.handle(_request(0, "initialize", {}))
    return srv


def _request(message_id, method, params=None):
    request = {"jsonrpc": "2.0", "id": message_id, "method": method}
    if params is not None:
        request["params"] = params
    return request


class TestInitialize:
    """Scenario: the MCP handshake."""

    def test_initialize_handshake(self):
        """
        Scenario: initialize returns server info and capabilities
          Given a fresh MCP server
          When the client sends initialize with protocolVersion 2024-11-05
          Then the server echoes the version, advertises tools+resources
            and identifies itself as brazilian-soccer-mcp
        """
        srv = MCPServer(dataset_loader=lambda: None)
        response = srv.handle(
            _request(
                1,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            )
        )
        assert response["id"] == 1
        result = response["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]
        assert result["serverInfo"]["name"] == "brazilian-soccer-mcp"
        assert result["serverInfo"]["version"]
        assert "Brazilian soccer" in result["instructions"]

    def test_initialize_echoes_known_protocol_versions(self):
        """
        Scenario: newer protocol versions are echoed back
          Given a fresh MCP server
          When the client requests protocolVersion 2025-06-18
          Then the server echoes 2025-06-18
        """
        srv = MCPServer(dataset_loader=lambda: None)
        response = srv.handle(
            _request(1, "initialize", {"protocolVersion": "2025-06-18"})
        )
        assert response["result"]["protocolVersion"] == "2025-06-18"

    def test_unknown_protocol_version_falls_back(self):
        """
        Scenario: an unknown protocol version falls back to the default
          Given a fresh MCP server
          When the client requests protocolVersion 1999-01-01
          Then the server answers with its default version
        """
        srv = MCPServer(dataset_loader=lambda: None)
        response = srv.handle(
            _request(1, "initialize", {"protocolVersion": "1999-01-01"})
        )
        assert response["result"]["protocolVersion"] == "2024-11-05"

    def test_requests_before_initialize_are_rejected(self):
        """
        Scenario: requests before initialize
          Given a fresh, un-initialised MCP server
          When the client calls tools/list immediately
          Then the server responds with error -32002
        """
        srv = MCPServer(dataset_loader=lambda: None)
        response = srv.handle(_request(1, "tools/list"))
        assert response["error"]["code"] == -32002

    def test_initialized_notification_is_acknowledged_silently(self):
        """
        Scenario: notifications produce no response
          Given an initialised MCP server
          When the client sends notifications/initialized
          Then the handler returns None
        """
        srv = MCPServer(dataset_loader=lambda: None)
        srv.handle(_request(1, "initialize", {}))
        assert (
            srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
            is None
        )


class TestToolListing:
    """Scenario: tools/list."""

    def test_tools_list_shape(self, server):
        """
        Scenario: every tool has a name, description and JSON schema
          Given the initialised server
          When the client lists tools
          Then all 14 tools are returned with object input schemas
        """
        server.handle(_request(0, "initialize", {}))
        response = server.handle(_request(2, "tools/list"))
        tools = response["result"]["tools"]
        assert {t["name"] for t in tools} == TOOL_NAMES
        assert len(tools) == 14
        for tool in tools:
            assert tool["description"]
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            assert isinstance(schema["properties"], dict)

    def test_ping(self, server):
        """
        Scenario: ping
          Given the initialised server
          When the client pings
          Then an empty result is returned
        """
        response = server.handle(_request(3, "ping"))
        assert response["result"] == {}


class TestToolCalls:
    """Scenario: tools/call dispatch and error semantics."""

    def test_search_matches_call(self, server):
        """
        Scenario: a successful tool call
          Given the initialised server with the dataset loaded
          When the client calls search_matches for Fla-Flu
          Then the result contains text content and structured content
            and isError is absent (false)
        """
        response = server.handle(
            _request(
                10,
                "tools/call",
                {
                    "name": "search_matches",
                    "arguments": {"team": "Flamengo", "opponent": "Fluminense"},
                },
            )
        )
        result = response["result"]
        assert "isError" not in result
        assert result["content"][0]["type"] == "text"
        text = result["content"][0]["text"]
        assert "Flamengo vs Fluminense" in text
        assert "more matches in dataset" in text  # truncated at limit 20
        assert result["structuredContent"]["ok"] is True
        assert result["structuredContent"]["total"] == 44

    def test_standings_call_renders_spec_format(self, server):
        """
        Scenario: a standings call renders the spec's answer format
          Given the initialised server with the dataset loaded
          When the client calls standings for serie_a 2019
          Then the text shows "1. Flamengo - 90 pts (28W, 6D, 4L)"
            and marks the champion
        """
        response = server.handle(
            _request(
                11,
                "tools/call",
                {
                    "name": "standings",
                    "arguments": {"competition": "serie_a", "season": 2019},
                },
            )
        )
        text = response["result"]["content"][0]["text"]
        assert "1. Flamengo - 90 pts (28W, 6D, 4L," in text
        assert "Champion" in text
        assert "Relegated (bottom 4)" in text

    def test_unknown_team_is_a_tool_error_not_protocol_error(self, server):
        """
        Scenario: execution errors set isError
          Given the initialised server with the dataset loaded
          When the client calls team_stats for a misspelled club
          Then the result has isError true and a helpful message
        """
        response = server.handle(
            _request(
                12,
                "tools/call",
                {
                    "name": "team_stats",
                    "arguments": {"team": "Flamengoo"},
                },
            )
        )
        result = response["result"]
        assert result.get("isError") is True
        assert "not found" in result["content"][0]["text"].lower()

    def test_unknown_tool_is_a_protocol_error(self, server):
        """
        Scenario: unknown tools use JSON-RPC error -32602
          Given the initialised server
          When the client calls a tool that does not exist
          Then the response is a -32602 error listing available tools
        """
        response = server.handle(
            _request(
                13,
                "tools/call",
                {
                    "name": "trade_players",
                    "arguments": {},
                },
            )
        )
        assert response["error"]["code"] == -32602
        assert "search_matches" in response["error"]["message"]

    def test_bad_arguments_are_protocol_errors(self, server):
        """
        Scenario: argument-type mistakes are rejected
          Given the initialised server
          When the client calls head_to_head without team_b
          Then the response is a -32602 error
        """
        response = server.handle(
            _request(
                14,
                "tools/call",
                {
                    "name": "head_to_head",
                    "arguments": {"team_a": "Flamengo"},
                },
            )
        )
        assert response["error"]["code"] == -32602


class TestProtocolErrors:
    """Scenario: JSON-RPC error handling."""

    def test_unknown_method(self, server):
        """
        Scenario: unknown request method
          Given the initialised server
          When the client requests resources/subscribe
          Then the response is -32601 method not found
        """
        response = server.handle(
            _request(20, "resources/subscribe", {"uri": "brazilian-soccer://overview"})
        )
        assert response["error"]["code"] == -32601

    def test_invalid_jsonrpc_version(self, server):
        """
        Scenario: a message that is not JSON-RPC 2.0
          Given the initialised server
          When the client sends jsonrpc "1.0"
          Then the response is -32600 invalid request
        """
        response = server.handle({"jsonrpc": "1.0", "id": 21, "method": "ping"})
        assert response["error"]["code"] == -32600

    def test_non_object_message(self, server):
        """
        Scenario: a message that is not an object
          Given the initialised server
          When the client sends a bare string
          Then the response is -32600 invalid request
        """
        response = server.handle("ping")
        assert response["error"]["code"] == -32600

    def test_batch_of_messages(self, server):
        """
        Scenario: a batch array maps to an array of responses
          Given the initialised server
          When the client sends [ping, notifications/initialized] as a batch
          Then one response (for the ping) comes back in an array
        """
        server.handle(_request(0, "initialize", {}))
        response = server.handle(
            [
                {"jsonrpc": "2.0", "id": 30, "method": "ping"},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
            ]
        )
        assert isinstance(response, list) and len(response) == 1
        assert response[0]["result"] == {}

    def test_tool_summaries_helper(self):
        """
        Scenario: the tool catalogue can be summarised for humans
          Given the tool descriptors
          Then one summary line per tool is produced
        """
        summary = tool_summaries()
        assert summary.count("\n") == len(TOOL_NAMES) - 1
        assert summary.startswith("- search_matches:")


class TestResources:
    """Scenario: MCP resources expose the datasets."""

    def test_resources_list(self, server):
        """
        Scenario: resource listing
          Given the initialised server
          When the client lists resources
          Then the overview, competitions and teams resources appear
            plus one resource per source CSV
        """
        response = server.handle(_request(40, "resources/list"))
        uris = [r["uri"] for r in response["result"]["resources"]]
        assert "brazilian-soccer://overview" in uris
        assert "brazilian-soccer://competitions" in uris
        assert "brazilian-soccer://teams" in uris
        assert "brazilian-soccer://dataset/Brasileirao_Matches.csv" in uris
        assert "brazilian-soccer://dataset/fifa_data.csv" in uris
        assert len(uris) == 9

    def test_resources_read_overview(self, server):
        """
        Scenario: reading the overview resource
          Given the initialised server
          When the client reads brazilian-soccer://overview
          Then the text describes the graph and normalisation approach
        """
        response = server.handle(
            _request(41, "resources/read", {"uri": "brazilian-soccer://overview"})
        )
        content = response["result"]["contents"][0]
        assert content["uri"] == "brazilian-soccer://overview"
        assert "Matches loaded" in content["text"]
        assert "Team-name normalisation" in content["text"]

    def test_resources_read_dataset(self, server):
        """
        Scenario: reading one dataset resource
          Given the initialised server
          When the client reads the fifa_data.csv resource
          Then columns, licence and source URL are included
        """
        response = server.handle(
            _request(
                42,
                "resources/read",
                {"uri": "brazilian-soccer://dataset/fifa_data.csv"},
            )
        )
        text = response["result"]["contents"][0]["text"]
        assert "Apache 2.0" in text
        assert "youssefelbadry10" in text

    def test_resources_read_unknown_uri(self, server):
        """
        Scenario: an unknown resource uri
          Given the initialised server
          When the client reads a uri that does not exist
          Then a -32602 error is returned
        """
        response = server.handle(
            _request(43, "resources/read", {"uri": "brazilian-soccer://nope"})
        )
        assert response["error"]["code"] == -32602


# --------------------------------------------------------------------------
# End-to-end: a real process over real pipes
# --------------------------------------------------------------------------


class _ServerSession:
    """Small wrapper around the spawned server's pipes."""

    def __init__(self, process):
        self.process = process

    def send_raw(self, text: str) -> None:
        self.process.stdin.write(text)
        self.process.stdin.flush()

    def talk(self, message: dict) -> dict | None:
        """Send a request and read its one response line."""
        self.send_raw(json.dumps(message) + "\n")
        return self.read()

    def notify(self, message: dict) -> None:
        """Send a notification (no response is ever written)."""
        self.send_raw(json.dumps(message) + "\n")

    def read(self) -> dict | None:
        line = self.process.stdout.readline()
        return json.loads(line) if line.strip() else None

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)


@pytest.fixture(scope="module")
def session():
    """Spawn the real server process and yield a _ServerSession helper."""
    import os
    from pathlib import Path

    process = subprocess.Popen(
        [sys.executable, "-m", "brazilian_soccer_mcp", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    wrapper = _ServerSession(process)
    yield wrapper
    wrapper.close()


class TestEndToEndOverStdio:
    """Scenario: a full client session against the spawned server."""

    def test_full_session(self, session):
        """
        Scenario: handshake, list tools, call a tool
          Given a spawned server process
          When the client initialises, acknowledges, lists tools
            and calls standings for the 2019 Brasileirão
          Then every request receives a valid JSON-RPC response
            and the standings answer names Flamengo as champion
        """
        init = session.talk(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            }
        )
        assert init["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"

        session.notify({"jsonrpc": "2.0", "method": "notifications/initialized"})

        listing = session.talk({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert len(listing["result"]["tools"]) == 14

        call = session.talk(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "standings",
                    "arguments": {"competition": "brasileirão", "season": 2019},
                },
            }
        )
        result = call["result"]
        assert "isError" not in result
        assert "1. Flamengo - 90 pts" in result["content"][0]["text"]
        assert result["structuredContent"]["champion"]["team"] == "Flamengo"

    def test_parse_error_line(self, session):
        """
        Scenario: a malformed line
          Given a spawned server process
          When the client writes something that is not JSON
          Then the server answers with a -32700 parse error
        """
        session.send_raw("this is not json\n")
        response = session.read()
        assert response["error"]["code"] == -32700

    def test_server_survives_empty_lines(self, session):
        """
        Scenario: blank lines are ignored
          Given a spawned server process
          When the client sends a blank line followed by ping
          Then only the ping is answered
        """
        session.send_raw("\n")
        response = session.talk({"jsonrpc": "2.0", "id": 9, "method": "ping"})
        assert response["id"] == 9
        assert response["result"] == {}

    def test_tool_error_over_the_wire(self, session):
        """
        Scenario: execution errors keep the session alive
          Given a spawned, initialised server
          When the client calls a tool with an unknown team
            and then pings again
          Then the tool result carries isError and the session still answers
        """
        session.talk({"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}})
        bad = session.talk(
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "player_search",
                    "arguments": {"position": "winger"},
                },
            }
        )
        assert bad["result"].get("isError") is True
        alive = session.talk({"jsonrpc": "2.0", "id": 12, "method": "ping"})
        assert alive["result"] == {}
