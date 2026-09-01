"""
Package init for the Brazilian Soccer MCP server.

Context block
-------------
Why:
    Single import point exposing the version and the most-used helpers so
    tests and clients do not depend on internal module layout.

What:
    ``brazilian_soccer_mcp`` assembles an in-memory knowledge graph from
    the six Kaggle CSVs (five match datasets + the FIFA player database)
    and serves queries through an MCP tool surface.
"""

__version__ = "1.0.0"

__all__ = ["dataset", "models", "normalize", "registry", "server", "service"]
