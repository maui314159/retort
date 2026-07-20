"""Brazilian Soccer MCP server package.

Context
-------
This package implements an MCP (Model Context Protocol) server that exposes a
knowledge-graph-style interface over Brazilian soccer datasets pre-downloaded
from Kaggle into ``data/kaggle/``.  The server lets an LLM answer natural
language questions about matches, teams, players, competitions, and statistics.

The implementation is organized as:

* ``normalize``   - team-name + date normalization helpers.
* ``data_loader`` - loads the six CSV datasets into unified ``Match`` / ``Player``
                    records plus a small in-memory ``KnowledgeGraph``.
* ``graph``       - the in-memory knowledge graph (teams, players, matches,
                    competitions as nodes connected by edges).
* ``queries``     - the query API (matches, teams, players, competitions, stats).
* ``formatters``  - human-readable text formatters matching the spec examples.
* ``server``      - the FastMCP entry point exposing the query API as MCP tools.

Data licenses: CC BY 4.0 (Brasileirão / Copa do Brasil / Libertadores / Histórico),
CC0 (BR-Football-Dataset), Apache 2.0 (FIFA players).  See TASK.md / README.md.
"""

from .data_loader import DataLoader, DATA_DIR
from .graph import KnowledgeGraph, Node, Edge
from .queries import SoccerQueries

__all__ = ["DataLoader", "DATA_DIR", "KnowledgeGraph", "Node", "Edge", "SoccerQueries"]
__version__ = "1.0.0"
