#!/usr/bin/env python3
"""Launcher for the Brazilian Soccer MCP server (stdio by default).

Usage:
    python server.py                  # stdio transport
    python server.py --transport streamable-http --port 8000
"""

from bsoccer.server import main

if __name__ == "__main__":
    main()
