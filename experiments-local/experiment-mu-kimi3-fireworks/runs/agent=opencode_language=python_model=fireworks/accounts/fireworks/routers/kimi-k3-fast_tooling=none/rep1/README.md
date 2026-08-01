# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md (same content as TASK.md)

## Implementation

A Python MCP server (`brazilian_soccer_mcp/`) that loads all six CSV files into
one unified, deduplicated match table plus the FIFA player table, and exposes
16 MCP tools for natural-language queries about matches, teams, players,
competitions and statistics.

### Architecture

| Module | Purpose |
|--------|---------|
| `brazilian_soccer_mcp/normalization.py` | Team-name normalization (state suffixes, aliases, accents), multi-format date parsing, team registry |
| `brazilian_soccer_mcp/data_loader.py` | Loads + unifies + deduplicates the 5 match CSVs; loads the FIFA player CSV |
| `brazilian_soccer_mcp/queries.py` | Query engine: matches, head-to-head, team records, standings, players, statistics |
| `brazilian_soccer_mcp/server.py` | FastMCP server exposing the query engine as MCP tools |

Team names are normalized across conventions, so `"Palmeiras-SP"`, `"Palmeiras"`,
`"palmeiras"` and `"Sport Club Corinthians Paulista"`/`"Corinthians-SP"` resolve
consistently. Dates accept ISO, ISO+time and Brazilian `DD/MM/YYYY`.
Overlapping fixtures that appear in several files are deduplicated (same-day,
same-fixture and adjacent-day passes), so league standings compute correctly
(e.g. 2019 Série A: Flamengo champion, 90 pts, 28W 6D 4L — the real record).

### Run

```bash
pip install -r requirements.txt
python -m brazilian_soccer_mcp            # MCP server over stdio
MCP_TRANSPORT=http python -m brazilian_soccer_mcp   # streamable HTTP on :8000
```

### Test

```bash
python -m pytest          # 168 tests: unit, functional, BDD (pytest-bdd) and MCP integration
```

### MCP tools

`dataset_info`, `list_teams`, `find_matches`, `last_match`, `head_to_head`,
`team_statistics`, `team_competitions`, `search_players`, `player_profile`,
`club_roster`, `competition_standings`, `competition_schedule`,
`biggest_victories`, `competition_overview`, `top_scoring_teams`,
`compare_seasons`.

### Data notes

- The extended file has no season column; seasons are derived (Jan–Mar league
  games belong to the previous season; cup games are cross-checked against the
  authoritative cup file).
- Known source-data limitations: the 2023 season exists only in the extended
  file (~377 of 380 Série A matches, so the computed 2023 table is slightly
  off); the histórico file lists Botafogo x Flamengo twice in 2009.
- The FIFA player database (FIFA 19) does not include Flamengo, Palmeiras,
  Corinthians, São Paulo or Vasco squads (licensing); club searches cover the
  Brazilian clubs that are present (Grêmio, Santos, Fluminense, ...).

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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
