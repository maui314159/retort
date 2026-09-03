"""Brazilian Soccer MCP server package.

A Model Context Protocol (MCP) server that exposes a knowledge graph of
Brazilian soccer data sourced from the bundled Kaggle CSVs in ``data/kaggle``.

The package is organised around four concerns:

* :mod:`brazilian_soccer_mcp.normalize` - normalisation helpers for team
  names, competition names and dates so that messy, multi-format source data
  can be matched consistently.
* :mod:`brazilian_soccer_mcp.data_loader` - loads all six CSV datasets into
  in-memory ``Match`` / ``Player`` records and exposes a unified registry.
* :mod:`brazilian_soccer_mcp.queries` - the query layer implementing the five
  capability categories required by the specification (match, team, player,
  competition and statistical queries).
* :mod:`brazilian_soccer_mcp.server` - the MCP server that surfaces the query
  layer as tools over the stdio transport.
"""

from .data_loader import SoccerData, load_all

__all__ = ["SoccerData", "__version__", "load_all"]
__version__ = "2.0.0"
