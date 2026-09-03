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

from . import normalizer
from .data import SoccerData, get_data, reset_cache
from .queries import QueryEngine, get_engine, reset_engine, resolve_competition

try:  # mcp is only needed for the server layer
    from .server import TOOL_REGISTRY, create_server, list_tool_names, main
except ImportError:  # pragma: no cover - mcp not installed
    create_server = None  # type: ignore
    main = None  # type: ignore
    list_tool_names = list  # type: ignore
    TOOL_REGISTRY = []  # type: ignore

__all__ = [
    "TOOL_REGISTRY",
    "QueryEngine",
    "SoccerData",
    "create_server",
    "get_data",
    "get_engine",
    "list_tool_names",
    "main",
    "normalizer",
    "reset_cache",
    "reset_engine",
    "resolve_competition",
]

__version__ = "2.0.0"
