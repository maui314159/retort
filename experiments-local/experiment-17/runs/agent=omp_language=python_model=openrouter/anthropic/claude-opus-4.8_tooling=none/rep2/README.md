# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a queryable knowledge base over pre-downloaded Kaggle datasets of
Brazilian soccer. An LLM client connected to the server can answer natural-language
questions about matches, teams, players, competitions, and aggregate statistics.

Specification: `TASK.md` (identical copy in `brazilian-soccer-mcp-guide.md`).

## What was implemented

A pure-Python, in-memory knowledge base (pandas) with a [FastMCP](https://modelcontextprotocol.io)
tool surface. No external services — everything runs off the bundled CSVs.

```
brazilian_soccer_mcp/
  normalize.py   team-name canonicalization (suffix/accent/case folding)
  loader.py      reads the 6 CSVs into unified, deduplicated in-memory tables
  knowledge.py   query engine (matches, teams, players, competitions, stats)
  formatting.py  renders structured results as readable text blocks
  server.py      FastMCP server exposing 11 query tools
tests/           BDD (Given-When-Then) pytest suite, run against the real data
```

### Data unification & correctness

The five match CSVs are projected into one unified `matches` table. Three of them
overlap on Brasileirão Série A but spell the same club irreconcilably differently
("Vasco" / "Vasco da Gama RJ", "Athletico" / "Atlético Paranaense"), so naive
row dedup cannot collapse duplicate fixtures. Two mechanisms solve this:

1. **Source partitioning** — each `(competition, season)` slice is sourced from
   exactly one CSV (highest priority present), so no cross-source duplicate
   fixtures can exist.
2. **State-aware identity keys** — team identity is `base|state` (e.g.
   `atletico|mg` vs `atletico|pr`), so distinct same-named clubs are never merged
   in standings or top-scorer aggregates, while *user queries* still match on the
   tolerant suffix-stripped base ("Flamengo" ↦ "Flamengo-RJ").

Validation: the computed 2019 Brasileirão table reproduces reality exactly —
Flamengo champion on 90 pts (28W 6D 4L), 20 teams each playing 38 games,
CSA/Chapecoense/Avaí/Cruzeiro relegated.

## MCP tools

| Tool | Capability |
|------|------------|
| `dataset_overview` | Loaded counts, competitions, season range |
| `search_matches` | Matches by team / opponent / competition / season / date range |
| `head_to_head` | Aggregate record between two teams |
| `team_record` | W/D/L, goals, win rate (optionally by season / competition / venue) |
| `team_competitions` | Competitions a team appears in |
| `search_players` | FIFA players by name / nationality / club / position / min rating |
| `players_by_club` | Per-club counts & average rating for a nationality |
| `league_standings` | League table computed from results (3-1-0) |
| `competition_statistics` | Avg goals/match, home/away/draw rates |
| `biggest_wins` | Largest goal-margin matches |
| `top_scoring_teams` | Teams ranked by goals scored |

Team names may be partial and need not include state suffixes; matching is
accent- and case-insensitive.

## Install & run

```bash
pip install -r requirements.txt        # mcp, pandas, pytest
python -m brazilian_soccer_mcp.server  # start the stdio MCP server
```

Point a client (e.g. Claude Desktop) at the command above. Set
`BRAZIL_SOCCER_DATA_DIR` to override the default `data/kaggle` location.

Quick programmatic check:

```python
from brazilian_soccer_mcp import KnowledgeBase
kb = KnowledgeBase()
print(kb.standings("Brasileirão Série A", 2019)[0])   # 2019 champion
```

## Tests

BDD Given-When-Then scenarios run against the real bundled datasets (no mocks):

```bash
python -m pytest -q        # 48 tests
```

Coverage: name normalization invariants, match/head-to-head queries, team &
competition stats (anchored to known 2019 standings), player search, aggregate
statistics, formatting output, and end-to-end MCP tool execution.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
