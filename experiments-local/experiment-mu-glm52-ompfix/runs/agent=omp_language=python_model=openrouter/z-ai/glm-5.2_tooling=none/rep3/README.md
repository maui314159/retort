# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a query interface over
Brazilian soccer datasets (matches, teams, competitions, players). Built to
the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was implemented

- **`soccer_data.py`** — Data-access layer. Loads and unifies the six Kaggle
  CSV datasets from `data/kaggle/` into one normalized `matches` table
  (~23,954 matches) plus the FIFA player table (~18,207 players), and exposes
  pure query methods (match search, head-to-head, team stats, standings,
  biggest wins, average goals, best record, derbies, player search, ...).
  Key normalization work:
  - `normalize_team()` resolves every team-name variant (`"Palmeiras-SP"`,
    `"América - MG"`, `"Atletico Mineiro"`, `"Athletico"`, ...) to a
    **canonical, disambiguated key** via a curated alias registry, so distinct
    clubs sharing a base name (Atlético-MG vs Atlético-GO) stay separate.
  - `normalize_comp()` preserves parentheticals so
    `"Brasileirão"` and `"Brasileirão (2003-2019)"` remain distinct datasets.
  - `parse_date()` handles ISO (`YYYY-MM-DD[ HH:MM:SS]`) and Brazilian
    (`DD/MM/YYYY`) formats; season is derived from the date when a source has
    no season column.
- **`mcp_server.py`** — FastMCP server exposing 15 tools:
  `search_matches`, `last_match`, `head_to_head`, `team_stats`,
  `team_competitions`, `standings`, `biggest_wins`, `average_goals`,
  `best_record`, `derbies`, `player_search`, `top_players`,
  `brazilians_at_brazilian_clubs`, `list_competitions`, `list_seasons`.
  Each tool returns JSON; the CSVs are loaded once and cached for the process.
- **`test_brazilian_soccer.py`** — BDD (Given/When/Then) pytest suite covering
  match, team, head-to-head, competition, statistical, player, derby,
  normalization, and MCP-tool-layer scenarios against the real datasets.
- **`requirements.txt`** — runtime and test dependencies.

## Data sources

| File | Dataset | License |
|------|---------|---------|
| `data/kaggle/Brasileirao_Matches.csv` | Brasileirão Serie A | CC BY 4.0 |
| `data/kaggle/Brazilian_Cup_Matches.csv` | Copa do Brasil | CC BY 4.0 |
| `data/kaggle/Libertadores_Matches.csv` | Copa Libertadores | CC BY 4.0 |
| `data/kaggle/BR-Football-Dataset.csv` | Extended match statistics | CC0 |
| `data/kaggle/novo_campeonato_brasileiro.csv` | Brasileirão 2003-2019 | CC BY 4.0 |
| `data/kaggle/fifa_data.csv` | FIFA player database | Apache 2.0 |

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running the MCP server

```bash
# stdio transport (default — for use with an MCP-compatible LLM client)
python mcp_server.py

# SSE transport
python mcp_server.py --transport sse --port 8000
```

## Running the tests

```bash
pytest -q
```

All 36 BDD scenarios pass.

## Example queries

- "Show me all Flamengo vs Fluminense matches" → `head_to_head("Flamengo","Fluminense")`
- "Who won the 2019 Brasileirão?" → `standings("Brasileirão", 2019)` → Flamengo (90 pts)
- "What is Corinthians' home record in 2022?" → `team_stats("Corinthians", competition="Brasileirão", season=2022, venue="home")`
- "Who are the top Brazilian players?" → `top_players(nationality="Brazil")`
- "Show me the biggest wins" → `biggest_wins()`
- "Show me all derbies in 2023" → `derbies(season=2023)`
