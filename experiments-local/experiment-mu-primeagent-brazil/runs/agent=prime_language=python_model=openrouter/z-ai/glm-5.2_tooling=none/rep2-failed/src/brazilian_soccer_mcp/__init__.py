"""
Context block
=============
Brazilian Soccer MCP Server - Package Init
-------------------------------------------
Public API:
  * QueryEngine / get_engine   - high level query API (tests use this directly)
  * get_data / SoccerData       - normalized data loader
  * normalizer                  - team name normalization helpers
  * create_server / main         - MCP server factory + stdio entrypoint

The data and query layers depend only on pandas. The MCP server layer depends
on the `mcp` package; its import is guarded so the rest of the package remains
usable even when `mcp` is not installed.
"""

from .data import SoccerData, get_data, reset_cache
from .queries import QueryEngine, get_engine, reset_engine, resolve_competition
from . import normalizer

try:  # mcp is only needed for the server layer
    from .server import create_server, main, list_tool_names, TOOL_REGISTRY
except ImportError:  # pragma: no cover - mcp not installed
    create_server = None  # type: ignore
    main = None  # type: ignore
    list_tool_names = lambda: []  # type: ignore
    TOOL_REGISTRY = []  # type: ignore

__all__ = [
    "SoccerData", "get_data", "reset_cache",
    "QueryEngine", "get_engine", "reset_engine", "resolve_competition",
    "normalizer", "create_server", "main", "list_tool_names", "TOOL_REGISTRY",
]

__version__ = "2.0.0"
