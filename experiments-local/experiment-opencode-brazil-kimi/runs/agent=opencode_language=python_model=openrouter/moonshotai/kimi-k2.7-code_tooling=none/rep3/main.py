"""
Top-level entry point for the Brazilian Soccer MCP server.

    python main.py

starts the server in stdio mode.
"""

from brazilian_soccer_mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
