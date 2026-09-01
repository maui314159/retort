"""Entry point for the Brazilian Soccer MCP server (stdio transport).

Usage::

    python run_server.py [--data-dir DATA_DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from brazilian_soccer_mcp.service import SoccerDataService
from brazilian_soccer_mcp.server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "kaggle",
        help="Directory containing the Kaggle CSV files",
    )
    args = parser.parse_args()
    SoccerDataService(args.data_dir)
    mcp.run()


if __name__ == "__main__":
    main()
