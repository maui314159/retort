# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Package init. Exposes the high-level QueryEngine and the FastMCP server
# factory so callers can `from brazilian_soccer_mcp import QueryEngine, build_server`.
# ============================================================================
from .data_loader import DataLoader
from .queries import QueryEngine
from .server import build_server, main

__all__ = ["DataLoader", "QueryEngine", "build_server", "main"]
__version__ = "2.0.0"
