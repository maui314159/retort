"""
Brazilian Soccer MCP Server package.

Context (Why): TASK.md ("Brazilian Soccer MCP Server - Specification") requires a
Model Context Protocol server exposing a queryable knowledge model over six
Kaggle-provided CSV datasets covering Brazilian soccer (5 match datasets + 1 FIFA
player dataset). The server is meant to be connected to an LLM so end users can
ask natural-language questions about players, teams, matches and competitions.

What lives where:
    models.py      -- core domain entities (Match, Player, TeamRecord ...)
    normalizer.py  -- team-name normalization / canonical identity registry
    loaders.py     -- CSV ingestion for all six datasets (multi-format dates,
                      UTF-8 Portuguese names, cross-source deduplication)
    service.py     -- the query/analytics engine (match search, head-to-head,
                      standings, player search, aggregate statistics)
    server.py      -- MCP tool surface (MCPServer from the official `mcp` SDK,
                      v2.x) wired to the service layer

Test: see tests/ (BDD given/when/then pytest suite).
Spec reference: TASK.md sections "Provided Data", "Required Capabilities",
"Success Criteria", "Testing Approach".
"""

__version__ = "1.0.0"
