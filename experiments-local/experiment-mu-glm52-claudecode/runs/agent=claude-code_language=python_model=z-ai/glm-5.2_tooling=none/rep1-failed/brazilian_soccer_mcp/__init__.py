"""Brazilian Soccer MCP server package.

Context
-------
Exposes a FastMCP server (built in :mod:`brazilian_soccer_mcp.server`)
that answers natural-language questions about Brazilian soccer over the
six provided Kaggle CSV datasets.  The package is also runnable directly
as ``python -m brazilian_soccer_mcp``.

Public API:

* :func:`build_server` — construct a fresh :class:`FastMCP` instance.
* :data:`mcp` — the module-level singleton server used by the entry point.
* :func:`load_dataset` — load + dedup the CSVs into a :class:`Dataset`.
* :class:`KnowledgeGraph` — adjacency-list graph over the dataset.
"""

from __future__ import annotations

from .loader import Dataset, load_dataset
from .knowledge_graph import KnowledgeGraph
from .server import build_server, mcp, get_knowledge_graph

__all__ = [
    "Dataset",
    "KnowledgeGraph",
    "build_server",
    "get_knowledge_graph",
    "load_dataset",
    "mcp",
]

__version__ = "1.0.0"
