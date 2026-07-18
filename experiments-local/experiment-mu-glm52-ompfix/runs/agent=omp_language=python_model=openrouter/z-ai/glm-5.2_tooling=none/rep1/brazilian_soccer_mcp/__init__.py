"""
brazilian_soccer_mcp
====================

Brazilian Soccer MCP (Model Context Protocol) server package.

A knowledge-graph interface over Brazilian soccer datasets (matches, players,
teams, competitions) that enables natural language queries via an LLM.

Modules
-------
* :mod:`models`            — domain dataclasses (Match, Player, Team, …)
* :mod:`normalize`         — team-name normaliser (handles suffixes, accents, collisions)
* :mod:`data_loader`       — loads the 6 Kaggle CSV files into typed records
* :mod:`knowledge_graph`   — in-memory graph with pre-built lookup indexes
* :mod:`query_engine`      — turns structured params into formatted answers
* :mod:`server`            — FastMCP server exposing query tools to an LLM
"""

from __future__ import annotations

__version__ = "2.0.0"
