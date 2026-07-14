"""
Brazilian Soccer MCP package.

This package provides a Model Context Protocol server and reusable query
engine for Brazilian football data.  The public modules are:

    - team_normalizer: canonicalizes team-name variations.
    - data_store: loads and unifies the six provided CSV datasets.
    - queries: high-level query functions used by the MCP server.
    - server: FastMCP-based MCP server exposing the query tools.
"""

from brazilian_soccer_mcp.data_store import DataStore, get_data_store
from brazilian_soccer_mcp.team_normalizer import normalize_team_name

__all__ = [
    "DataStore",
    "get_data_store",
    "normalize_team_name",
]
