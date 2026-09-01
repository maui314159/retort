"""Brazilian Soccer MCP server package."""

from .data_loader import Match, Player, load_all
from .queries import KnowledgeBase

__all__ = ["KnowledgeBase", "Match", "Player", "load_all"]
__version__ = "1.0.0"
