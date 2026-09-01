"""Brazilian Soccer MCP server package."""

from .data_loader import Dataset, Match, Player
from .queries import QueryEngine

__version__ = "1.0.0"

__all__ = ["Dataset", "Match", "Player", "QueryEngine", "__version__"]
