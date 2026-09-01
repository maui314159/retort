"""Brazilian Soccer MCP Server package.

A Model Context Protocol (MCP) server exposing a knowledge interface over
six Brazilian soccer datasets (five match archives + the FIFA 19 player
database) stored as CSV under ``data/kaggle/``.

Package layout
--------------
``normalize``  team-name identity resolution, dates, parsing
``models``     Match/Player dataclasses
``loader``     CSV -> normalized objects, cross-source de-duplication
``store``      SoccerStore: indexes and all query methods
``analytics``  pure statistical computations (standings, records, ...)
``tools``      deterministic natural-language question router
``server``     FastMCP application exposing tools + resources over stdio
"""

from .store import NotFound, SoccerStore

__all__ = ["SoccerStore", "NotFound"]
__version__ = "1.0.0"
