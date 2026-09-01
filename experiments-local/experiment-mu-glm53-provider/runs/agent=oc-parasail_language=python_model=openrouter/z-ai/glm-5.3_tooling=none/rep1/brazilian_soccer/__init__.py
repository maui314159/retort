"""Brazilian soccer MCP server package.

Context: implements the Model Context Protocol server specified in
TASK.md — a knowledge service over six Kaggle datasets covering
Brasileirão, Copa do Brasil and Copa Libertadores matches (2003-2023)
plus a FIFA player database. The package is dependency-free (stdlib
only); see server.py for the entry point.
"""

from .models import Match, Player, TeamEntity
from .normalize import clean_text, parse_date, split_team
from .repository import DataRepository

__version__ = "1.0.0"

__all__ = [
    "DataRepository",
    "Match",
    "Player",
    "TeamEntity",
    "clean_text",
    "parse_date",
    "split_team",
    "__version__",
]
