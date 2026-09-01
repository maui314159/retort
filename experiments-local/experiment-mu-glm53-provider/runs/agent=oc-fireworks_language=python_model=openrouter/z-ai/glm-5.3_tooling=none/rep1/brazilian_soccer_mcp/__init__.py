"""
brazilian_soccer_mcp - MCP server & knowledge graph for Brazilian soccer.

Package layout (see module docstrings for the full design notes):

* normalizer.py - team/competition/date normalisation (alias tables).
* loader.py     - loads the six Kaggle CSVs, dedups overlapping fixtures,
                 builds the club registry and all indexes.
* models.py     - Match / Player / Club / StandingRow dataclasses.
* queries.py    - every capability required by the spec (one function each).
* render.py     - human-formatted answers (shared by MCP tools and CLI).
* tools.py      - MCP tool catalogue + dispatch.
* server.py     - MCP stdio server (newline-delimited JSON-RPC 2.0).
* cli.py        - direct command-line access to the same queries.

Run the MCP server:  python -m brazilian_soccer_mcp
Run the CLI:         python -m brazilian_soccer_mcp.cli --help
Run the tests:       python -m pytest
"""

from .loader import Dataset, load_dataset

__version__ = "1.0.0"

__all__ = ["Dataset", "__version__", "load_dataset"]
