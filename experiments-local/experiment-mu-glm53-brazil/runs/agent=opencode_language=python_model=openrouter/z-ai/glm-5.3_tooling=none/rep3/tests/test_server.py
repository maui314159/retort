"""
BDD GWT scenarios: the MCP server surface.

Gherkin counterpart: ``tests/features/server.feature``.

Covers TASK.md "Overview": an MCP server exposing the knowledge base over
the Model Context Protocol.  Verifies tool registration, JSON-serializable
responses and a full stdio JSON-RPC round trip against ``server.py``.
"""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
from pathlib import Path

from brazilian_soccer_mcp import service as svc
from brazilian_soccer_mcp.server import build_server, list_registered_tools

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TOOLS = {
    "search_matches",
    "head_to_head",
    "last_match",
    "derby_matches",
    "team_record",
    "team_profile",
    "list_teams",
    "resolve_team",
    "find_players",
    "top_players",
    "players_at_club",
    "standings",
    "champion",
    "bracket",
    "competition_info",
    "season_averages",
    "biggest_wins",
    "match_statistics",
}


class TestToolRegistry:
    def test_given_the_server_when_built_then_all_expected_tools_registered(self):
        # Given the FastMCP application
        # When built
        mcp = build_server("test-server")
        # Then every documented tool is registered with a description
        tools = {t.name: t for t in list_registered_tools(mcp)}
        assert EXPECTED_TOOLS <= set(tools)
        for name in EXPECTED_TOOLS:
            assert tools[name].description, f"tool {name} lacks a description"

    def test_given_every_tool_when_called_via_service_then_json_serializable(self, dataset):
        # Given representative calls for every tool's service function
        # When executed
        outputs = {
            "search_matches": svc.search_matches(dataset, team="Flamengo", season=2019, limit=3),
            "head_to_head": svc.head_to_head(dataset, "Palmeiras", "Santos"),
            "last_match": svc.last_match(dataset, "Flamengo"),
            "derby_matches": svc.derby_matches(dataset, season=2023),
            "team_record": svc.team_record(dataset, "Corinthians", season=2022, venue="home"),
            "team_profile": svc.team_profile(dataset, "Palmeiras"),
            "list_teams": svc.list_teams(dataset, "Brasileirão Serie A", 2019),
            "resolve_team": svc.resolve_team_info(dataset, "Flamengo"),
            "find_players": svc.find_players(dataset, nationality="Brazil", limit=3),
            "top_players": svc.top_players(dataset, nationality="Brazil", limit=3),
            "players_at_club": svc.players_at_club(dataset, "Grêmio"),
            "standings": svc.standings(dataset, "Brasileirão Serie A", 2019),
            "champion": svc.champion(dataset, "Copa Libertadores", 2019),
            "bracket": svc.bracket(dataset, "Copa do Brasil", 2019),
            "competition_info": svc.competition_info(dataset, "libertadores"),
            "season_averages": svc.season_averages(dataset, "Brasileirão Serie A", 2019),
            "biggest_wins": svc.biggest_wins(dataset, limit=3),
            "match_statistics": svc.match_statistics(dataset, team="Flamengo", season=2023, limit=2),
        }
        # Then every output round-trips through JSON (MCP transport requirement)
        for name, payload in outputs.items():
            assert json.dumps(payload) is not None, f"{name} is not JSON-serializable"


class TestStdioRoundTrip:
    def test_given_the_running_server_when_jsonrpc_issued_then_tools_answer(self):
        # Given the server launched as an MCP stdio subprocess
        # When the client initializes, lists tools and calls one
        # Then valid JSON-RPC responses come back
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
            env=env,
        )
        try:
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "bdd-test", "version": "1.0"},
                    },
                },
            )
            init = self._recv(proc, timeout=60)
            assert init["id"] == 1
            assert "serverInfo" in init["result"]

            self._send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            self._send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            listing = self._recv(proc, timeout=30)
            tool_names = {t["name"] for t in listing["result"]["tools"]}
            assert EXPECTED_TOOLS <= tool_names

            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "champion",
                        "arguments": {"competition": "Brasileirão Serie A", "season": 2019},
                    },
                },
            )
            answer = self._recv(proc, timeout=60)
            payload = json.loads(answer["result"]["content"][0]["text"])
            assert payload["champion"] == "Flamengo"

            # Expected failures surface their guidance to the LLM client.
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "standings",
                        "arguments": {"competition": "Copa do Brasil", "season": 2019},
                    },
                },
            )
            error = self._recv(proc, timeout=30)
            text = error["result"]["content"][0]["text"]
            assert "knockout competition" in text
            assert "bracket" in text
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    @staticmethod
    def _send(proc: subprocess.Popen, message: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _recv(proc: subprocess.Popen, timeout: float) -> dict:
        assert proc.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        try:
            deadline = timeout
            while True:
                events = selector.select(timeout=deadline)
                if not events:
                    raise TimeoutError("MCP server did not respond in time")
                line = proc.stdout.readline()
                if not line.strip():
                    continue
                return json.loads(line)
        finally:
            selector.unregister(proc.stdout)
            selector.close()


class TestEntrypoint:
    def test_given_the_package_when_installed_style_import_then_main_exists(self):
        # Given the console-script entry point
        from brazilian_soccer_mcp.server import main

        # Then it is callable
        assert callable(main)
