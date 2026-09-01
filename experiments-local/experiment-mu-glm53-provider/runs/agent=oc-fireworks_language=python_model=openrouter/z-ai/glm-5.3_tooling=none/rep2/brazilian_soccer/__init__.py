"""Brazilian Soccer MCP server package.

Loads the six Kaggle datasets into an in-memory knowledge graph and exposes
query capabilities as MCP tools (see :mod:`server`).
"""

from .loader import SoccerData
from .service import SoccerService

__all__ = ["SoccerData", "SoccerService"]

__version__ = "1.0.0"
