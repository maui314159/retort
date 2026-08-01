#!/usr/bin/env python3
"""Entry point for the Brazilian Soccer MCP server.

Runs the server over stdio (the transport MCP clients such as Claude
Desktop use by default)::

    python server.py

Data directory resolution: ``data/kaggle`` next to this file, or override
with the ``SOCCER_DATA_DIR`` environment variable.
"""

from soccer_mcp.mcp_server import main

if __name__ == "__main__":
    main()
