"""Brazilian Soccer MCP server package.

A knowledge-graph-style query engine over the Kaggle datasets in
``data/kaggle/`` plus an MCP (Model Context Protocol) server front-end.

Main entry points:

* :func:`brsoccer.data.load_default` -- load all six CSV datasets into a
  :class:`brsoccer.data.SoccerData` container.
* :func:`brsoccer.data.SoccerData` -- the query engine (matches, teams,
  players, competitions, statistics).
* :mod:`brsoccer.mcp_server` -- MCP tool wiring (stdio server).
"""

from .data import SoccerData, load_default
from .models import Match, Player, TableRow

__version__ = "2.0.0"

__all__ = ["SoccerData", "load_default", "Match", "Player", "TableRow", "__version__"]
