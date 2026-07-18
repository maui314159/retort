# brazilian_soccer
# -----------------------------------------------------------------------------
# MCP server exposing a knowledge-graph-style query interface over Brazilian
# soccer datasets (Brasileirão, Copa do Brasil, Libertadores, FIFA players).
#
# Package layout:
#   models.py    - dataclasses (Match, TeamRecord, Standing, Player)
#   normalize.py - team-name normalization (accent folding, suffix stripping)
#   loader.py    - CSV loading + deduplication -> pandas DataFrames
#   queries.py   - query engine (matches, teams, players, competitions, stats)
#   server.py    - FastMCP server registering every query as an MCP tool
# -----------------------------------------------------------------------------
from __future__ import annotations

__version__ = "1.0.0"
