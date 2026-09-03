"""Brazilian Soccer MCP server.

A Model Context Protocol (MCP) server that exposes a knowledge graph of
Brazilian soccer data (Brasileirao, Copa do Brasil, Copa Libertadores and a
FIFA player database) as queryable MCP tools.

Public entry points
-------------------
* :class:`brsl.knowledge_graph.KnowledgeGraph` - in-memory graph store.
* :class:`brsl.query_engine.QueryEngine`       - the query API.
* :func:`brsl.server.build_server`              - build the MCP server.
* :func:`brsl.server.main`                      - run it over stdio.
"""
from __future__ import annotations

from .knowledge_graph import KnowledgeGraph
from .query_engine import QueryEngine, get_engine

__all__ = ["KnowledgeGraph", "QueryEngine", "get_engine", "__version__"]
__version__ = "0.2.0"
