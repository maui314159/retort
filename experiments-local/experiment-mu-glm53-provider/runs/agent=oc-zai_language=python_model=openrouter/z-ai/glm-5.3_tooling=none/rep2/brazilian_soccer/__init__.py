"""Brazilian Soccer MCP server package.

Provides a Model Context Protocol server exposing a query interface over
Brazilian soccer datasets (matches, teams, players, competitions) loaded
from the CSV files in ``data/kaggle``.
"""

from brazilian_soccer.data import Dataset, load_dataset

__all__ = ["Dataset", "load_dataset"]
