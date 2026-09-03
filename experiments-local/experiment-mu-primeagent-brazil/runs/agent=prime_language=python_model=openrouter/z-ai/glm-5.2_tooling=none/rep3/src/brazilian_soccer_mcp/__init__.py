"""
Brazilian Soccer MCP Server
===========================

A Model Context Protocol (MCP) server that exposes a knowledge-graph
interface over Brazilian soccer data (matches, teams, players, and
competitions) sourced from freely-available Kaggle datasets.

The package is organised as follows:

* ``normalizer``   – team-name and date normalisation utilities.
* ``data_loader``  – loads and unifies the six raw CSV files.
* ``knowledge_graph`` – in-memory graph of nodes (Team / Player /
  Match / Competition) and edges (PLAYED_IN, IN_COMPETITION,
  MEMBER_OF, …).
* ``queries``      – high-level query engine used by the MCP tools.
* ``server``       – the MCP server that exposes the queries as
  callable tools.

All public query results are plain Python dictionaries so they can be
serialised to JSON and returned over the MCP transport.
"""

__version__ = "2.0.0"
__all__ = ["normalizer", "data_loader", "knowledge_graph", "queries", "server"]
