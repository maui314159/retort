"""Brazilian Soccer MCP Server.

A Model Context Protocol (Model Context Protocol) server that exposes a
knowledge-graph-style query interface over the provided Brazilian soccer
datasets (Brasileirão, Copa do Brasil, Copa Libertadores, an extended
match-statistics dataset, the historical 2003-2019 Brasileirão archive,
and a FIFA player database).

The package is organised as follows:

- ``brazilian_soccer.normalize``  : team-name / date normalisation helpers
- ``brazilian_soccer.data_loader``: loads & unifies the CSV datasets
- ``brazilian_soccer.queries``    : pure query functions (no I/O)
- ``brazilian_soccer.server``     : the FastMCP server exposing tools

Run the server with ``python -m brazilian_soccer``.
"""

from .data_loader import Data, get_data

__all__ = ["Data", "get_data"]
__version__ = "2.0.0"
