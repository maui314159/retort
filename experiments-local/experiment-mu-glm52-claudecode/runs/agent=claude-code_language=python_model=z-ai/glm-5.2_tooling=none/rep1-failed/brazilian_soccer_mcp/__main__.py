"""Stdio entry point: ``python -m brazilian_soccer_mcp``.

Context
-------
Launches the FastMCP server over the MCP stdio transport so an MCP client
(an LLM agent) can discover and call the Brazilian-soccer tools.  The
knowledge graph is built lazily on the first tool call via
:func:`brazilian_soccer_mcp.server.get_knowledge_graph`, so importing the
package is cheap and the process only pays the CSV-load cost when a query
actually arrives.
"""

from __future__ import annotations

from .server import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
