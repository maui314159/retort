"""
Entry point: ``python -m brazilian_soccer_mcp`` runs the MCP stdio server.
"""

from .server import main

if __name__ == "__main__":
    raise SystemExit(main())
