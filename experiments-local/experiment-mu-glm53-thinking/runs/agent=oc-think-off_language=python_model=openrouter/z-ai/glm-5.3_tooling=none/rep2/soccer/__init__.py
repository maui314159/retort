"""Brazilian Soccer MCP Server package.

Provides a data-loading layer over the Kaggle CSV datasets, a query
layer (matches, teams, players, competitions, statistics) and an MCP
server exposing those queries as tools.
"""

from soccer.loader import SoccerData, load_soccer_data
from soccer.models import Match, Player
from soccer.normalize import normalize_name, normalize_player_name

__all__ = [
    "Match",
    "Player",
    "SoccerData",
    "load_soccer_data",
    "normalize_name",
    "normalize_player_name",
]
