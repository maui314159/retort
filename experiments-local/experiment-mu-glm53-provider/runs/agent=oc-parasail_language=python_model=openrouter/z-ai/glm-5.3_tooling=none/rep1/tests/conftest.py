"""Shared fixtures: a loaded repository and a live MCP server process."""

from __future__ import annotations

import json
import select
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brazilian_soccer.repository import DataRepository


@pytest.fixture(scope="session")
def repo() -> DataRepository:
    return DataRepository(ROOT / "data" / "kaggle")


class MCPClient:
    """Minimal MCP stdio client driving the real server subprocess."""

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self._next_id = 0

    def send(self, payload: dict) -> None:
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

    def read(self, timeout: float = 30.0) -> dict:
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("MCP server did not respond in time")
        line = self.process.stdout.readline()
        if not line:
            raise AssertionError("MCP server closed stdout unexpectedly")
        return json.loads(line)

    def request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        response = self.read()
        assert response.get("id") == self._next_id
        return response

    def notify(self, method: str, params: dict | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def call_tool(self, name: str, arguments: dict) -> dict:
        response = self.request(
            "tools/call", {"name": name, "arguments": arguments}
        )
        assert "result" in response, response
        result = response["result"]
        assert result["content"][0]["type"] == "text"
        if result.get("isError"):
            raise AssertionError(f"tool error: {result['content'][0]['text']}")
        return json.loads(result["content"][0]["text"])

    def close(self) -> None:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        self.process.wait(timeout=30)


@pytest.fixture(scope="session")
def mcp() -> MCPClient:
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py")],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    client = MCPClient(process)
    response = client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.0.0"},
        },
    )
    assert "result" in response
    client.notify("notifications/initialized")
    yield client
    client.close()
