"""
Context
=======
Brazilian Soccer MCP Server - top-level package.

Provides a knowledge-graph-style query interface over six Kaggle Brazilian
soccer datasets (matches + FIFA players) exposed as an MCP (Model Context
Protocol) server.  See ``TASK.md`` for the full specification and the module
docstrings of :mod:`soccer_mcp.normalize`, :mod:`soccer_mcp.data_loader`,
:mod:`soccer_mcp.queries` and :mod:`soccer_mcp.server` for implementation
details.

Public submodules
-----------------
* ``normalize``    - team name / date / goal canonicalisation.
* ``data_loader``  - CSV loading + source-priority merge into SoccerData.
* ``queries``      - pure query functions (matches, teams, players, comps, stats).
* ``server``       - MCP tool registration + stdio runner.

Quick start
-----------
    from soccer_mcp.queries import find_matches, standings
    find_matches(team="Flamengo", opponent="Fluminense", limit=5)
    standings("Brasileirao Serie A", "2019")
"""

from __future__ import annotations

__all__ = ["normalize", "data_loader", "queries", "server"]

__version__ = "1.0.0"
