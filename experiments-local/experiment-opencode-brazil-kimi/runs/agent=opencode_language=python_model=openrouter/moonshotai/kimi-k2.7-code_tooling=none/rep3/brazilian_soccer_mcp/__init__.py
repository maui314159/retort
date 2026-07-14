"""
Brazilian Soccer MCP Server
===========================

A Model Context Protocol (MCP) server that surfaces Brazilian football data
from the Kaggle datasets bundled under ``data/kaggle``. The package exposes
three layers:

* ``normalize``  – text/date/score normalization helpers.
* ``data_loader`` – CSV ingestion, name canonicalisation and deduplication.
* ``engine``     – read-only query engine used by both tests and the server.
* ``server``     – MCP stdio server implemented with ``mcp.server.fastmcp``.

Version 1.0.0
"""

__version__ = "1.0.0"
