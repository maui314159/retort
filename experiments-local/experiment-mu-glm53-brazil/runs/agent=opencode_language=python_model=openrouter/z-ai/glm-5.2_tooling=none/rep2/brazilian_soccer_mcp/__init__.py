# SPDX-License-Identifier: Apache-2.0
# Brazilian Soccer MCP Server
# Context block ---------------------------------------------------------------
# Package: brazilian_soccer_mcp
# Purpose: Expose the public API for the Brazilian soccer knowledge graph.
# Layers:
#   - team_normalize: canonical team-name keys for cross-file matching
#   - data_loader:    load/parse all 6 Kaggle CSV datasets into Match/Player rows
#   - models:         typed dataclasses for Match, Player, TeamStats, Standing
#   - queries:        high-level query functions (matches, teams, players, ...)
#   - server:         MCP server exposing those queries as tools
# Data sources live under data/kaggle/ (CC BY 4.0 / CC0 / Apache 2.0).
# --------------------------------------------------------------------------- #
"""Brazilian Soccer MCP server package."""

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.queries import QueryEngine

__all__ = ["DataLoader", "QueryEngine", "__version__"]
__version__ = "1.0.0"
