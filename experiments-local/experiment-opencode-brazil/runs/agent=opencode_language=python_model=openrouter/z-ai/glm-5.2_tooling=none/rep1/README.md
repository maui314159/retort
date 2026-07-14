# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a query engine over the
provided Brazilian soccer Kaggle datasets. It lets an LLM answer natural-language
questions about players, teams, matches and competitions.

The full specification lives in [`TASK.md`](TASK.md) and
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was implemented

* `brazilian_soccer_mcp/normalizers.py` — team-name canonicalization
  (state suffixes, accents, full names, alias map + data-driven base/state
  resolution so e.g. `CSA-AL`, `CSA` and `Csa-AL` all resolve to `csa` while
  `Atlético-MG` and `Atlético-GO` stay distinct), multi-format date parsing,
  and a curated derby list.
* `brazilian_soccer_mcp/data_loader.py` — loads all six CSVs into a single
  unified match table, **deduplicates** matches that appear in several sources
  (Brasileirão overlaps the historical 2003-2019 file and the BR-Football
  `Serie A` file; Copa do Brasil overlaps BR-Football), keeps a `sources`
  list per unique match, and keeps a separate extended-stats table (corners,
  shots, attacks) from the BR-Football dataset.
* `brazilian_soccer_mcp/query_engine.py` — `QueryEngine` with methods for all
  five required categories: match queries, team queries, player queries,
  competition queries and statistical analysis.
* `brazilian_soccer_mcp/models.py` — dataclasses for `Match`, `Player`,
  `TeamStats`, `StandingRow`, `HeadToHead`.
* `brazilian_soccer_mcp/mcp_server.py` — a `FastMCP` server exposing 17 tools
  that wrap the engine and return JSON.

## Datasets used

All six files in `data/kaggle/` are loaded and queryable:

| File | Rows | Used for |
|------|------|----------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão matches (2012-2022) |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores |
| `BR-Football-Dataset.csv` | 10,296 | Brasileirão / Serie B / Serie C / Copa do Brasil + extended stats |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão (2003-2019) |
| `fifa_data.csv` | 18,207 | FIFA player database |

## MCP tools

`search_matches`, `head_to_head`, `team_statistics`, `top_teams_by_record`,
`most_goals_scored`, `search_player`, `top_players`, `players_at_club`,
`competition_standings`, `competition_champion`, `relegated_teams`,
`average_goals_per_match`, `home_vs_away_performance`, `biggest_wins`,
`derbies`, `match_stats`, `data_coverage`.

## Installation

```bash
pip install -e .
```

## Running the server

```bash
brazilian-soccer-mcp
# or
python -m brazilian_soccer_mcp.mcp_server
```

The data directory defaults to `data/kaggle`; override with the
`BRAZILIAN_SOCCER_DATA` environment variable.

## Testing

BDD (Given/When/Then) style tests with `pytest`:

```bash
pytest -q
```

Tests cover normalization, match queries, team queries, player queries,
competition queries, statistical analysis and the MCP server tools. Example
scenarios validated against the data:

* 2019 Brasileirão champion → **Flamengo, 90 pts (28W 6D 4L)**
* 2019 relegated teams include **Avai** (20th)
* Top Brazilian player → **Neymar Jr, Overall 92**
* Fla-Flu head-to-head, average goals per match, biggest wins, derbies.

## Architecture notes

* Aggregations (standings, head-to-head, averages) run on the **deduplicated**
  match table so overlapping sources do not double-count. Dedup key is
  `(competition, season, home_id, away_id)` — safe for league and cup
  fixtures where each ordered pair meets once per season.
* Team normalization is layered: an explicit alias map handles major clubs
  whose base name is shared across states (Botafogo-RJ vs Botafogo-SP), and a
  data-driven fallback strips a trailing state code only when that base name
  is unambiguous in the dataset (so `Ceará-CE` → `ceara` but
  `Santa Cruz-PE`/`Santa Cruz-RN` stay distinct).
