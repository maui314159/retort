#!/usr/bin/env python
"""
Entry point: Brazilian Soccer MCP server (stdio transport).

Context block
-------------
Why:
    TASK.md requires an MCP server; MCP clients launch servers as
    subprocesses with a stdio JSON-RPC transport, so a thin launcher script
    at the repository root is the most client-friendly entry point.

What:
    Delegates to ``brazilian_soccer_mcp.server:main`` (FastMCP stdio).
    Configure any MCP client with:
        {"command": "python", "args": ["<repo>/server.py"]}
    or install the package and use the ``brazilian-soccer-mcp`` console
    script.

Test:
    Covered by the stdio round-trip scenario in ``tests/test_server.py``.

Spec references:
    TASK.md "Overview" and "References" -> MCP Protocol
    (https://modelcontextprotocol.io).
"""

from brazilian_soccer_mcp.server import main

if __name__ == "__main__":
    main()
