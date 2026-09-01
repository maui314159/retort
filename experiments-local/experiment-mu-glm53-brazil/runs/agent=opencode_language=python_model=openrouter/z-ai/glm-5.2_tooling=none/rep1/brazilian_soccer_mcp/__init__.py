"""
Brazilian Soccer MCP Server package.

Context block
=============
Purpose: Provide a Model Context Protocol (MCP) server exposing a knowledge
graph / query interface over Brazilian soccer datasets (match results from
Brasileirao, Copa do Brasil, Copa Libertadores, an extended statistics
dataset, historical Brasileirao 2003-2019, and a FIFA player database).

Modules
-------
- ``data_loader`` : loads, normalizes and indexes every CSV under
  ``data/kaggle/``. Handles team-name variations, multiple date formats and
  UTF-8 encoding.
- ``queries``     : pure-Python query API (matches, teams, players,
  competitions, statistical analysis) consumed by the MCP tool layer.
- ``mcp_server``  : stdio MCP server (JSON-RPC 2.0) declaring the query API
  as callable tools.

Why no external runtime deps
----------------------------
Only the Python standard library plus the ``mcp`` SDK are required so the
package builds and runs in a minimal virtualenv. CSV parsing uses the stdlib
``csv`` module; date parsing uses ``datetime``.
"""

from .data_loader import DataLoader
from .queries import SoccerQueryEngine

__all__ = ["DataLoader", "SoccerQueryEngine"]
__version__ = "1.0.0"
