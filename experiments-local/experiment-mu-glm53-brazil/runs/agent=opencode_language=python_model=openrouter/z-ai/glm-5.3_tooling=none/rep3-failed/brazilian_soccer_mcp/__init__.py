"""Brazilian Soccer MCP server package.

An MCP (Model Context Protocol) server exposing a knowledge-graph style
interface over six Kaggle datasets covering Brazilian soccer: match results
for the Brasileirão (2003-2023), Copa do Brasil (2012-2023), Copa
Libertadores (2013-2022), extended match statistics (2014-2023) and the FIFA
player database.
"""

__version__ = "1.0.0"

from brazilian_soccer_mcp.loader import load_data
from brazilian_soccer_mcp.queries import QueryEngine, find_data_dir, get_engine

__all__ = ["QueryEngine", "find_data_dir", "get_engine", "load_data", "__version__"]
