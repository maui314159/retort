"""End-to-end stdio transport test: spawn server.py and speak MCP JSON-RPC."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER = PROJECT_ROOT / "server.py"


@pytest.fixture()
def stdio_server():
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=PROJECT_ROOT,
    )
    yield proc
    proc.terminate()
    proc.wait(timeout=10)


def _send(proc, message):
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _read(proc):
    line = proc.stdout.readline()
    assert line.strip(), "server closed stdout"
    return json.loads(line)


class TestStdioTransport:
    def test_given_running_server_when_initialized_then_server_info_returned(self, stdio_server):
        _send(
            stdio_server,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            },
        )
        response = _read(stdio_server)
        assert response["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"

    def test_given_initialized_server_when_tools_listed_then_tools_returned(self, stdio_server):
        _send(
            stdio_server,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "0"}},
            },
        )
        _read(stdio_server)
        _send(stdio_server, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(stdio_server, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        response = _read(stdio_server)
        tools = response["result"]["tools"]
        assert len(tools) >= 19
        assert any(t["name"] == "search_matches" for t in tools)

    def test_given_initialized_server_when_tool_called_then_answer_returned(self, stdio_server):
        _send(
            stdio_server,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "0"}},
            },
        )
        _read(stdio_server)
        _send(stdio_server, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(
            stdio_server,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "standings", "arguments": {"competition": "Série A", "season": 2019}},
            },
        )
        response = _read(stdio_server)
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["champion"]["team"] == "Flamengo (RJ)"
        assert payload["champion"]["points"] == 90
