"""Run the Brazilian Soccer MCP server (stdio transport).

    python -m brazilian_soccer
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
