"""Entry point for the Brazilian Soccer MCP server (stdio transport).

Usage:
    python main.py            # stdio transport (for MCP clients)
"""

from __future__ import annotations

import os
import sys

from brazilian_soccer.data import load_dataset
from brazilian_soccer.server import create_server


def main() -> None:
    data_dir = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    dataset = load_dataset(data_dir)
    server = create_server(dataset)
    server.run(transport="stdio")


if __name__ == "__main__":
    sys.exit(main())
