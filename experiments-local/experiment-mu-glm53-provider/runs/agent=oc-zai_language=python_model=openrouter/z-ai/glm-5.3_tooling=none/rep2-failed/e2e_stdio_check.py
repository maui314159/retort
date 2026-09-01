"""Manual end-to-end check: drive the MCP server over stdio JSON-RPC.

Not part of the pytest suite (keeps the suite fast); run with::

    python e2e_stdio_check.py
"""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def send(payload: dict) -> None:
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    def recv() -> dict:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout: " + proc.stderr.read())
        return json.loads(line)

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "e2e-check", "version": "1.0"},
    }})
    init = recv()
    assert "serverInfo" in init["result"], init
    print("initialize ->", init["result"]["serverInfo"]["name"])

    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = recv()
    names = [t["name"] for t in tools["result"]["tools"]]
    print(f"tools/list -> {len(names)} tools")
    assert "search_matches" in names and "get_standings" in names

    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "get_standings",
        "arguments": {"competition": "brasileirao", "season": 2019},
    }})
    result = recv()
    text = result["result"]["content"][0]["text"]
    payload = json.loads(text)
    champion = payload["data"]["champion"]
    print("get_standings 2019 -> champion:", champion)
    assert champion == "Flamengo", payload

    send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "get_head_to_head",
        "arguments": {"team_a": "Flamengo", "team_b": "Fluminense"},
    }})
    result = recv()
    payload = json.loads(result["result"]["content"][0]["text"])
    print("head_to_head Fla-Flu ->", payload["data"]["total_meetings"], "meetings")
    assert payload["data"]["total_meetings"] > 30

    proc.stdin.close()
    proc.wait(timeout=10)
    print("E2E OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
