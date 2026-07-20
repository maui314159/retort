"""Brazilian Soccer MCP server package.

Exposes a knowledge-graph-style query interface over Brazilian soccer
datasets (matches, players, competitions, statistics) via the Model
Context Protocol.
"""

from .data import Dataset, get_dataset

__all__ = ["Dataset", "get_dataset"]
__version__ = "1.0.0"
