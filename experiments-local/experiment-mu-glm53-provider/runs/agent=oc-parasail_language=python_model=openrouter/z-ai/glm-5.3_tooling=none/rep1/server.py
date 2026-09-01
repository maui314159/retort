#!/usr/bin/env python3
"""Brazilian Soccer MCP server entry point.

Context: runs the Model Context Protocol server over stdio (the standard
transport for local MCP servers). Point an MCP client at this file, e.g.
`python server.py`, and ask questions about Brazilian soccer in natural
language. Two helper modes exist for manual testing without an MCP client:

    python server.py --list-tools                  # print tool schemas
    python server.py --invoke search_matches --args '{"team": "Flamengo"}'

Datasets are loaded once at startup from data/kaggle/ (see TASK.md for
attribution and licenses).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from brazilian_soccer import __version__
from brazilian_soccer.protocol import MCPStdioServer, build_dataset_resources
from brazilian_soccer.repository import DataRepository
from brazilian_soccer.tools import build_tool_registry

INSTRUCTIONS = (
    "Brazilian soccer knowledge server: matches (Brasileirão Serie A/B/C "
    "2003-2023, Copa do Brasil 2012-2023, Copa Libertadores 2013-2022), "
    "team records and standings, head-to-head comparisons, and a FIFA "
    "player database. Prefer find_team for unusual spellings; team names "
    "accept state suffixes like 'America-MG' to disambiguate."
)


def create_server(data_dir: str | None = None) -> MCPStdioServer:
    repo = DataRepository(data_dir)
    tools = build_tool_registry(repo)
    resources = build_dataset_resources(repo)
    return MCPStdioServer(
        server_name="brazilian-soccer-mcp",
        server_version=__version__,
        tools=tools,
        resources=resources,
        instructions=INSTRUCTIONS,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory containing the Kaggle CSV files (default: data/kaggle)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print the MCP tool schemas as JSON and exit",
    )
    parser.add_argument(
        "--invoke",
        metavar="TOOL",
        help="Run one tool directly (for manual testing) and print its JSON result",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help='JSON object of tool arguments for --invoke (default: {})',
    )
    options = parser.parse_args(argv)

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    server = create_server(options.data_dir)

    if options.list_tools:
        print(json.dumps(server._tools_list(), ensure_ascii=False, indent=2))
        return 0

    if options.invoke:
        try:
            arguments = json.loads(options.args)
        except json.JSONDecodeError as error:
            print(f"Invalid --args JSON: {error}", file=sys.stderr)
            return 2
        try:
            result = server._tools_call({"name": options.invoke, "arguments": arguments})
        except Exception as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
            return 1
        for block in result.get("content", []):
            print(block.get("text", ""))
        return 1 if result.get("isError") else 0

    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
