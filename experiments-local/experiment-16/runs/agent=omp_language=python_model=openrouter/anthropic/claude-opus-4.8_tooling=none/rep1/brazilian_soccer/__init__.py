"""
================================================================================
Context
--------------------------------------------------------------------------------
Package : brazilian_soccer
Purpose : Knowledge-graph interface over Brazilian soccer datasets, exposed as
          an MCP (Model Context Protocol) server for natural-language queries
          about players, teams, matches and competitions.

Data    : Six pre-downloaded Kaggle CSVs under data/kaggle/ (see README.md).
          Five are match datasets (Brasileirao, Copa do Brasil, Libertadores,
          an extended-statistics set, and a historical 2003-2019 set); one is
          the FIFA player database.

Design  : Everything is loaded once into an in-memory graph (teams, players,
          matches as nodes; PLAYED / PLAYS_FOR as edges) backed by plain Python
          structures + pandas for ingestion. No external database is required,
          which keeps simple lookups well under the 2s budget and aggregate
          queries under 5s while remaining fully unit-testable offline.

Modules :
  normalize  - team-name / date / score normalization helpers
  loader     - reads the CSVs into a uniform list of MatchRecord / PlayerRecord
  graph      - SoccerGraph: indexes records and answers structured queries
  server     - FastMCP server wiring the graph queries to MCP tools
================================================================================
"""

from .graph import SoccerGraph
from .loader import load_graph, MatchRecord, PlayerRecord

__all__ = ["SoccerGraph", "load_graph", "MatchRecord", "PlayerRecord"]
