"""Brazilian Soccer MCP server package.

Provides a knowledge-base over six Kaggle CSV datasets (Brasileirão,
Copa do Brasil, Copa Libertadores, historical 2003-2019 Série A, extended
match statistics and the FIFA player database) plus an MCP server
(:mod:`server`) exposing the query surface as tools.
"""

from .loaders import KnowledgeBase, load_knowledge_base
from .service import SoccerDataService

__version__ = "1.0.0"

__all__ = ["KnowledgeBase", "load_knowledge_base", "SoccerDataService", "__version__"]
