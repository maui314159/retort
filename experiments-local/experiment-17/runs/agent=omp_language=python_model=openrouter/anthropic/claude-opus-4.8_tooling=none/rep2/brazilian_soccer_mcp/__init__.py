"""
Context
=======
Package: brazilian_soccer_mcp
Purpose: An MCP (Model Context Protocol) server exposing a queryable knowledge
         base over pre-downloaded Kaggle datasets of Brazilian soccer (matches,
         competitions, and FIFA player attributes).

Layout
------
    normalize.py   -- team-name canonicalization (pure functions)
    loader.py      -- read the six CSVs into normalized in-memory tables
    knowledge.py   -- query engine: matches, teams, players, competitions, stats
    formatting.py  -- render query results as human-readable text blocks
    server.py      -- FastMCP server wiring the engine to MCP tools

The knowledge base is loaded once into pandas DataFrames held in memory, which
keeps every documented query well under the 2s/5s latency budget.
"""

from __future__ import annotations

from .knowledge import KnowledgeBase

__all__ = ["KnowledgeBase"]
