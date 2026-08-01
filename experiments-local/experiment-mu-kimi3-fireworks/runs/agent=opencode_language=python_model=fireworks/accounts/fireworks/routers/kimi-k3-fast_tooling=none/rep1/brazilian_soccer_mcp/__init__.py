"""Brazilian Soccer MCP server package.

A knowledge-graph style MCP interface over six Kaggle datasets of
Brazilian soccer: match results (Brasileirão, Copa do Brasil, Copa
Libertadores) and the FIFA player database.
"""

from .data_loader import SoccerDataset, get_dataset, load_matches, load_players
from .normalization import TeamRegistry, normalize_text, parse_date, team_key
from .queries import QueryEngine, resolve_competition

__version__ = "1.0.0"

__all__ = [
    "QueryEngine",
    "SoccerDataset",
    "TeamRegistry",
    "get_dataset",
    "load_matches",
    "load_players",
    "normalize_text",
    "parse_date",
    "resolve_competition",
    "team_key",
]
