"""Brazilian soccer knowledge base.

Loads the six Kaggle CSV datasets in data/kaggle/ and provides normalized,
cross-file query functions used by the MCP server in server.py.
"""

from .data import KAGGLE_DIR, SoccerData, get_soccer_data
from .normalize import display_name, team_key

__all__ = [
    "KAGGLE_DIR",
    "SoccerData",
    "display_name",
    "get_soccer_data",
    "team_key",
]
