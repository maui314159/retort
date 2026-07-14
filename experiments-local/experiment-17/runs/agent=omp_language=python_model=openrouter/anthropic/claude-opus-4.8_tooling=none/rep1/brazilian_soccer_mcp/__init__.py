"""
Context
=======
Package: brazilian_soccer_mcp

An MCP (Model Context Protocol) server providing a knowledge-graph interface
over Brazilian soccer data (matches across Brasileirão Série A/B/C, Copa do
Brasil and Copa Libertadores, plus the FIFA player database).

Layering (bottom-up):
    normalize.py    - team-name + date normalisation primitives.
    data_loader.py  - reads the six Kaggle CSVs into a unified, deduplicated
                      KnowledgeBase (matches + players frames).
    queries.py      - pure, testable query/aggregation functions.
    server.py       - thin FastMCP adapter exposing queries as MCP tools.

The query layer is deliberately decoupled from the protocol so it can be used
directly (and is exercised by the BDD test-suite) without an MCP client.
"""

from __future__ import annotations

from .data_loader import KnowledgeBase, build_knowledge_base, get_knowledge_base

__all__ = ["KnowledgeBase", "build_knowledge_base", "get_knowledge_base"]
__version__ = "1.0.0"
