"""Brazilian Soccer MCP server package.

Loads the Kaggle datasets in ``data/kaggle`` and exposes query functions
used by the MCP server in ``server.py``.
"""

from .loader import SoccerData, load_soccer_data
from .models import Match, Player

__all__ = ["Match", "Player", "SoccerData", "load_soccer_data"]
