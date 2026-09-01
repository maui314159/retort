"""
server.py -- entry point of the Brazilian Soccer MCP server.

CONTEXT
-------
Runs the Model Context Protocol server (stdio transport) exposing the 20
soccer tools defined in ``soccer_mcp.tools``.  Use it with any MCP client,
e.g. add to claude_desktop_config.json:

    {
      "mcpServers": {
        "brazilian-soccer": {
          "command": "python",
          "args": ["/path/to/server.py"]
        }
      }
    }

or run directly:  python server.py

The datasets under data/kaggle/ are loaded once at first tool call and cached
for the lifetime of the process (~1s load, in-memory queries afterwards).
Only the MCP protocol is written to stdout -- nothing else prints, ever.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the package importable when server.py is run from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from soccer_mcp import tools  # noqa: E402

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_INSTRUCTIONS = (
    "Knowledge tools about Brazilian soccer: matches (Brasileirão Série A "
    "2003-2023, Copa do Brasil 2012-2023, Libertadores 2013-2022, Série B/C "
    "2014-2023), teams, standings, finals, head-to-head records, derby "
    "fixtures and FIFA player data.  Team names can be given in any spelling "
    "found in the datasets (e.g. 'Flamengo', 'Flamengo-RJ'); when a name is "
    "ambiguous the tools list candidates."
)


def build_server() -> MCPServer:
    """Create the MCPServer and register every public tool."""
    server = MCPServer(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)
    for name, function in sorted(vars(tools).items()):
        if name.startswith("_") or not callable(function):
            continue
        if getattr(function, "__module__", None) != tools.__name__:
            continue
        server.tool(name=name, description=function.__doc__ or None)(function)
    return server


def main() -> None:
    """Run the MCP server over stdio."""
    server = build_server()
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
