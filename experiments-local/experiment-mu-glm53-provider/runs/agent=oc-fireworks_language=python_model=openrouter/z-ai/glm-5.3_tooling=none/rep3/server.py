#!/usr/bin/env python3
"""Brazilian Soccer MCP server entry point (stdio transport).

Usage::

    python server.py

Configure with an MCP client (Claude Desktop, opencode, etc.)::

    {
      "mcpServers": {
        "brazilian-soccer": {
          "command": "python",
          "args": ["<path-to>/server.py"]
        }
      }
    }
"""

from brsoccer.mcp_server import main

if __name__ == "__main__":
    main()
