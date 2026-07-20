"""Brazilian Soccer MCP server package.

A knowledge-graph style interface over the Kaggle Brazilian soccer datasets
located in ``data/kaggle/`` (Brasileirão, Copa do Brasil, Copa Libertadores,
extended match statistics, historical Brasileirão 2003-2019 and the FIFA
player database).
"""

from .data import DataStore
from .queries import QueryEngine

__all__ = ["DataStore", "QueryEngine"]
__version__ = "1.0.0"
