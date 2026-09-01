"""Brazilian Soccer MCP Server package.

Provides a Model Context Protocol (MCP) server exposing a knowledge-graph
interface over Brazilian soccer datasets (matches, competitions, players).

Modules
-------
models           Dataclasses for matches, players and team records.
normalize        Text/date/team-name normalization helpers.
clubs            Curated registry of Brazilian clubs (aliases, FIFA names, derbies).
loaders          CSV loaders for the six Kaggle datasets.
knowledge_graph  In-memory property knowledge graph (nodes + typed edges).
engine           Query engine implementing match, team, player, competition
                 and statistical queries with formatted answers.
"""

__version__ = "1.0.0"
