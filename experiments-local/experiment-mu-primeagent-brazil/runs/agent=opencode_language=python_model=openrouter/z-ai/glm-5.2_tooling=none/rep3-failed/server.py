"""
Context
=======
Entry point for the Brazilian Soccer MCP server.

Run with::

    python server.py

This builds the MCP server (see :mod:`soccer_mcp.server`) and serves it over
stdio so any MCP-aware LLM client (Claude Desktop, etc.) can call its tools to
answer natural-language questions about Brazilian soccer.
"""

from __future__ import annotations

from soccer_mcp.server import main

if __name__ == "__main__":
    main()
