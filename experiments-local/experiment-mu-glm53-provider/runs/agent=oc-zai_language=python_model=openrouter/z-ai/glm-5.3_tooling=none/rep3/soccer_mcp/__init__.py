"""
soccer_mcp -- Brazilian Soccer MCP server package.

CONTEXT
-------
Implements the Brazilian Soccer MCP Server specification (TASK.md /
brazilian-soccer-mcp-guide.md): a Model Context Protocol server that answers
natural-language questions about Brazilian soccer from six pre-downloaded
Kaggle datasets in data/kaggle/.

Module map:
    normalize     -- team-name canonicalization, competition/date parsing
    model         -- shared dataclasses (Match, Player, TeamEntity, ...)
    data_loader   -- CSV ingestion, team registry, dedup + source selection
    queries       -- pure analytical query functions
    formatting    -- renders results in the spec's answer formats
    tools         -- the MCP tool functions registered by server.py
    bdd           -- tiny Given/When/Then harness used by the BDD test suite
"""

__version__ = "1.0.0"
