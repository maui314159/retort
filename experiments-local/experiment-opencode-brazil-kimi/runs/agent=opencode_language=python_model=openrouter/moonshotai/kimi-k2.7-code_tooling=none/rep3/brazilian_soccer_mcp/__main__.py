"""
Entry point for running the Brazilian Soccer MCP server as a module.

    python -m brazilian_soccer_mcp

starts the server in stdio mode.
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
