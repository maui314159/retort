# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes Brazilian soccer datasets
(matches, players) as queryable tools for an LLM client. Built per the
specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## What was implemented

- **`brazilian_soccer_mcp/normalizers.py`** — canonical team-name keys (strips
  state suffixes like `-SP` / ` - MG`, removes accents/parentheticals, applies
  full-name overrides like `Sport Club Corinthians Paulista` → `Corinthians`),
  multi-format date parsing (`YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`,
  `DD/MM/YYYY`), and competition-label normalization (`Serie A` →
  `Brasileirao`).
- **`brazilian_soccer_mcp/data_loader.py`** — loads all 6 Kaggle CSVs from
  `data/kaggle/`, unifies them into a single `Match` dataclass (competition,
  season, date, teams, scores, round/stage/stadium, etc.), and **deduplicates**
  matches that appear in more than one source file (e.g. Brasileirão 2012–2022
  is covered by both `Brasileirao_Matches.csv` and `BR-Football-Dataset.csv`).
  Loads the FIFA player DataFrame and adds `club_key` / `nationality_key` for
  cross-file joins.
- **`brazilian_soccer_mcp/queries.py`** — the `QueryEngine`: match lookup by
  team/opponent/competition/season/date-range, head-to-head, team stats
  (W/D/L, GF/GA, win rate, home/away filter), player search (name, nationality,
  club, position, min rating), standings + champion + relegation (calculated
  from match results), average goals / win rates, biggest wins, best home/away
  record.
- **`brazilian_soccer_mcp/server.py`** — a `FastMCP` server exposing 16 tools
  (`find_matches`, `head_to_head`, `team_stats`, `search_players`,
  `top_brazilian_players`, `players_at_club`, `standings`, `champion`,
  `relegated_teams`, `average_goals`, `biggest_wins`, `best_home_record`,
  `best_away_record`, `list_teams`, `list_competitions`, `list_seasons`).

## Data coverage

| File | Records | Loaded as |
|------|---------|-----------|
| `Brasileirao_Matches.csv` | 4,180 | `Brasileirao` |
| `Brazilian_Cup_Matches.csv` | 1,337 | `Copa do Brasil` |
| `Libertadores_Matches.csv` | 1,255 | `Copa Libertadores` |
| `BR-Football-Dataset.csv` | 10,296 | normalized per `tournament` column |
| `novo_campeonato_brasileiro.csv` | 6,886 | `Brasileirao (2003-2019)` |
| `fifa_data.csv` | 18,207 | FIFA player DataFrame |

After deduplication, **22,733 unique matches** + **18,207 players** are
queryable in memory. Simple lookups return in well under 2 seconds.

## Install

```bash
pip install -e ".[dev]"
```

## Run the MCP server (stdio)

```bash
brazilian-soccer-mcp        # console script
# or
python -m brazilian_soccer_mcp.server
```

## Use the engine directly

```python
from brazilian_soccer_mcp import QueryEngine
eng = QueryEngine()
print(eng.champion("Brasileirao", 2019))      # Flamengo
print(eng.head_to_head("Flamengo", "Fluminense"))
print(eng.top_brazilian_players(5))
```

## Tests

BDD (GWT) scenarios with `pytest-bdd` plus unit tests:

```bash
pytest -q
```

Features covered:
- `tests/features/match_queries.feature` — match lookup, team stats, H2H,
  competition filtering.
- `tests/features/player_queries.feature` — top Brazilians, name search, min
  rating filter.
- `tests/features/competition_queries.feature` — standings, champion,
  relegation, average goals.
- `tests/test_normalizers.py` — team-key/date/competition edge cases and MCP
  tool registration.

## Data sources & licenses

See `README.md` history and `TASK.md`. Datasets are CC BY 4.0 / CC0 / Apache 2.0
from Kaggle; this project is for demo / non-commercial use.
