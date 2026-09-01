# Architecture summary

`brazilian_soccer_mcp` — a Model Context Protocol server over six Kaggle CSV
datasets, layered cleanly:

- **`loader.py`** (509 LOC) — `SoccerData.load()` reads the six CSVs in
  `data/kaggle/` with `csv.DictReader`, normalizes them into `Match` /
  `Player` records and builds lookup indexes (`matches_by_team`,
  `players_by_club`, `players_by_nationality`, a case-folded `known_teams`
  alias map). No external APIs; pure local data.
- **`models.py`** (161 LOC) — `Match`, `Player` dataclasses + result helpers.
- **`normalize.py`** (452 LOC) — team-name canonicalization (handles
  `Flamengo`/`Flamengo-RJ` style variants), competition-label normalization,
  date parsing.
- **`service.py`** (852 LOC) — `SoccerQueryService`, the query engine: match
  filtering (team/opponent/competition/season/date/venue/stage), team
  W/L/D records, head-to-head, standings computed from match results,
  aggregate statistics, player search/filter, season comparison.
- **`server.py`** (337 LOC) — `build_server()` registers 18 MCP tools over the
  service using `mcp.server.mcpserver.MCPServer` (the mcp 2.1.x rename of
  FastMCP). `__main__.py` runs it over stdio.

**Tests** (`tests/`, 78 functions, 0 skips) — BDD-style suites per capability
plus an end-to-end stdio JSON-RPC round-trip. All pass; coverage 0.95.
