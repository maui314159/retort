"""Brazilian soccer knowledge base for the MCP server.

Loads the six Kaggle CSV datasets, normalizes team names to canonical
keys, unifies overlapping competition seasons and exposes analysis
functions over matches, teams, players, competitions and statistics.
"""

from .loader import SoccerData, load_soccer_data
from .normalize import TeamRegistry, team_key

__all__ = [
    "SoccerData",
    "load_soccer_data",
    "TeamRegistry",
    "team_key",
    "__version__",
]

__version__ = "1.0.0"
