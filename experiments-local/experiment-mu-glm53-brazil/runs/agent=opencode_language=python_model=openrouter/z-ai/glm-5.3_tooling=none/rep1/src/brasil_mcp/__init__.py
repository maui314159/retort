"""Brazilian Soccer MCP server package.

Provides a Model Context Protocol server exposing a knowledge-graph style
query interface over six Kaggle datasets covering Brazilian soccer matches
(Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores) and FIFA player
data.
"""

from .store import SoccerStore

__version__ = "1.0.0"

__all__ = ["SoccerStore", "__version__"]
