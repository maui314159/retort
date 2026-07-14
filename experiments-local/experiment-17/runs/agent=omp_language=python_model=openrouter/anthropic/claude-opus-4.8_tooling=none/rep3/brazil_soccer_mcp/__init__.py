"""
================================================================================
Brazilian Soccer MCP Server
================================================================================
Context:
    An MCP (Model Context Protocol) server exposing a knowledge-graph interface
    over Brazilian soccer datasets (matches across Brasileirao / Copa do Brasil
    / Copa Libertadores, plus a FIFA player database). It answers natural
    language style queries about matches, teams, players, competitions and
    aggregated statistics.

Architecture:
    - data/kaggle/*.csv          : provided source datasets (read-only)
    - normalize.py               : team-name / date / competition normalization
    - loaders.py                 : CSV -> normalized Match / Player records
    - graph.py                   : in-memory knowledge graph + query engine
    - formatting.py              : human-readable response rendering
    - server.py                  : FastMCP server exposing query tools

Design choice:
    The knowledge graph is held in memory (built from the CSVs at load time).
    This needs no external database, runs anywhere, and satisfies the spec's
    performance targets (simple lookups < 2s, aggregates < 5s).

License: Apache-2.0. Datasets retain their original licenses (see README.md).
================================================================================
"""

from .graph import KnowledgeGraph, build_graph
from .loaders import DATA_DIR, Match, Player

__all__ = ["KnowledgeGraph", "build_graph", "Match", "Player", "DATA_DIR"]
__version__ = "1.0.0"
