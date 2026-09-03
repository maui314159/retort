# Brazilian Soccer MCP

An MCP (Model Context Protocol) server that exposes a **knowledge graph** of
Brazilian soccer data — Brasileirão, Copa do Brasil, Copa Libertadores, and a
FIFA player database — as queryable MCP tools.

## What was built

* `brsl/normalization.py`  — canonical team-name normalization that collapses the
  many naming variants across the source files (state suffixes `-SP`, foreign
  country codes `(URU)`, accented vs unaccented forms, `FC` prefixes, …) into a
  single ASCII key while preserving the Brazilian state / country for
  disambiguation (e.g. `Atlético-MG` vs `Atlético-PR`).
* `brsl/data_loader.py`    — loads all six bundled CSV files into one unified
  match `DataFrame` plus the FIFA player `DataFrame`. Handles ISO and
  Brazilian date formats, UTF-8/BOM, and provides `load_matches_deduplicated()`
  which removes the same physical match duplicated across files.
* `brsl/knowledge_graph.py` — an in-memory graph (`Team`, `Player`, `Match`,
  `Competition` nodes with participation/membership edges) materialised from the
  de-duplicated matches. No external database is required (the benchmark runs
  without provisioning a graph DB).
* `brsl/query_engine.py`   — the high-level query API covering all five required
  capability areas: match queries, team queries, player queries, competition
  queries and statistical analysis, plus head-to-head comparisons and derby
  detection. All results are JSON-serialisable.
* `brsl/server.py`         — the MCP server (`mcp` v2 SDK, `MCPServer`) exposing
  18 tools and runnable over stdio.
* `tests/`                — BDD (Given/When/Then) structured pytest suite.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## Install

```bash
pip install -e .            # installs brsl + the `brsl-server` console script
# or, for development:
pip install -r requirements-dev.txt && pip install -e .
```

## Run the MCP server

```bash
brsl-server          # stdio transport (the default for MCP clients)
python -m brsl.server
```

An MCP client (e.g. Claude Desktop, opencode, etc.) can launch this server and
call its tools. The available tools are:

`search_matches`, `head_to_head`, `team_stats`, `team_competitions`,
`team_summary`, `search_players`, `top_brazilian_players`,
`players_at_brazilian_clubs`, `team_players`, `standings`, `champion`,
`relegated`, `cup_bracket`, `average_goals`, `home_vs_away`,
`biggest_victories`, `top_scoring_teams`, `derbies`.

## Example queries

```python
from brsl.query_engine import get_engine
q = get_engine()

q.champion("brasileirao", 2019)
# -> champion: "Flamengo-RJ", points: 90, record: [28, 6, 4]

q.head_to_head("Flamengo", "Fluminense")
# -> matches, wins/draws/losses and goals for each side

q.team_stats("Corinthians", season=2022, competition="brasileirao", venue="home")
q.top_brazilian_players(limit=5)
q.biggest_victories("libertadores", limit=3)
q.derbies(season=2023)
```

## Tests

BDD/GWT structured tests with pytest:

```bash
pytest -q
```

## Notes on data quality

* Several matches appear in more than one source file (e.g. the 2019
  Brasileirão is in both `Brasileirao_Matches.csv` and
  `novo_campeonato_brasileiro.csv`, and `BR-Football-Dataset.csv` overlaps with
  all of them). `load_matches_deduplicated()` collapses these, and
  standings/season statistics additionally use a single preferred source per
  `(competition, season)` so computed point totals match real-world tables
  (Flamengo 90 pts, 28W/6D/4L in 2019).
* Ambiguous club names such as `Atlético` / `América` are disambiguated using
  the Brazilian state suffix; the two 2019 Atléticos (MG, PR) appear as separate
  standings rows.
* The FIFA snapshot does not include every Brazilian club (e.g. Flamengo is
  absent), so cross-file player lookups for such clubs legitimately return 0
  players.
