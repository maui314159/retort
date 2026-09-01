# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that provides a knowledge-graph style
query interface over six Kaggle datasets covering Brazilian soccer: matches
from the Brasileirão Série A (2003-2023), Série B/C (2014-2023), Copa do
Brasil (2012-2023) and Copa Libertadores (2013-2022), plus a FIFA player
database (18,207 players).

Connect it to any MCP client (Claude Desktop, Claude Code, or any LLM with
an MCP harness) and ask natural-language questions such as *"Who won the
2019 Brasileirão?"*, *"Show me all derbies in 2023"* or *"Which team has the
best away record?"*.

## What was implemented

Per `TASK.md` / `brazilian-soccer-mcp-guide.md`:

- **Match queries** - by team, opponent, competition, season, date range,
  stage (`final`, `round 22`, ...) and venue (home/away), across all five
  match datasets, with head-to-head summaries.
- **Team queries** - win/draw/loss records with goals, home/away splits,
  per-competition and per-season breakdowns, side-by-side team comparison.
- **Player queries** - FIFA player search by name, nationality, club,
  position (code or group) and rating filters; Brazilian squads by team name.
- **Competition queries** - standings computed from match results (champion
  + relegation zone), Libertadores stage-by-stage brackets, dataset coverage.
- **Statistical analysis** - average goals per match, home/away win rates,
  biggest victories, best records by points-per-game, curated derby pairs
  (Fla-Flu, Grenal, Majestoso, Ba-Vi, Atletiba, ...).
- **Data quality handling** - team-name canonicalization across very
  different naming conventions, multiple date formats, UTF-8 accented names,
  cross-file deduplication, and COVID-season boundary corrections.

### Architecture

```
src/brasil_mcp/
  dates.py      multi-format date parsing (ISO, Brazilian, NA sentinels)
  normalize.py  team-name canonicalization (aliases, state suffixes, accents)
  models.py     Match / Player / TeamRecord dataclasses
  loaders.py    one loader per CSV file
  store.py      unified in-memory store: dedup, indexes, query methods
  queries.py    formatted, spec-style answers (summary + structured data)
  server.py     MCP server exposing 14 tools (stdio transport)
  cli.py        brasil-soccer command line interface
tests/          BDD (Gherkin Given/When/Then) pytest suite
```

The store loads all six CSVs once (~1.5 s), merges duplicate records and
indexes by team, so simple lookups answer in milliseconds.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -e .
pytest                      # run the BDD test suite
```

## Running the MCP server

```bash
python -m brasil_mcp.server        # stdio transport (for MCP clients)
brasil-soccer-mcp                  # installed console script
```

Client configuration (see `mcp-client-config.example.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brasil_mcp.server"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `find_team` | Resolve any spelling variant; matches, seasons, titles, squad |
| `search_matches` | Filter matches by team/opponent/competition/season/date/stage/venue |
| `head_to_head` | All-time record between two teams |
| `team_stats` | W/D/L + goals, home/away, per-competition, per-season |
| `team_season_history` | Season-by-season trend |
| `standings` | Computed league table, champion, relegation zone; Libertadores bracket |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `team_players` | FIFA squad of a Brazilian club |
| `competition_info` | What competitions/seasons the datasets cover |
| `derbies` | Matches between traditional rivals |
| `biggest_wins` | Largest goal-margin victories |
| `goals_analysis` | Averages and home/away win rates |
| `best_records` | Teams ranked by points per game |
| `compare_teams` | Side-by-side comparison with head-to-head |

Every tool returns a JSON payload containing a ready-to-display `summary`
string (in the format of the spec's example answers) plus the structured
data behind it.

## CLI examples

```bash
brasil-soccer standings --season 2019
brasil-soccer h2h Palmeiras Santos
brasil-soccer stats Corinthians --season 2022 --competition "Série A"
brasil-soccer matches --team Flamengo --opponent Fluminense --limit 5
brasil-soccer players --nationality Brazil --min-overall 88
brasil-soccer squad Grêmio
brasil-soccer derbies --season 2023
brasil-soccer biggest-wins --competition Libertadores
brasil-soccer goals --competition "Série A" --season 2023
brasil-soccer best-records --venue away
brasil-soccer find-team "Sport Club Corinthians Paulista"
```

## Data handling notes

**Team-name canonicalization.** The datasets write the same club as
`Palmeiras-SP`, `Palmeiras`, `América - MG`, `America MG`, `Sport Club
Corinthians Paulista`, `Athletico-PR` / `Atlético-PR`, ... All variants fold
onto one canonical id (`palmeiras-sp`) via state-suffix parsing, an alias
table of official names, legal-word filtering (`FC`, `EC`, `Clube`, ...) and
accent-insensitive matching. Ambiguous bases keep their state suffix in
display names (e.g. `América-MG` vs `América-RN`), and same-name foreign
clubs are kept apart (`Santos` vs `Santos-AP` vs `Santos Laguna`).

**Cross-file deduplication.** The 2012-2022 Série A seasons exist in up to
three files. Matches are grouped by (competition, season, home, away) and
merged when dates are at most 4 days apart - the datasets show true
duplicates differ by 1-2 days (timezone drift) while legitimately distinct
meetings (Libertadores group vs knockout) are 14+ days apart. Postponed
matches that appear once with the scheduled date (no result) and once with
the played date are absorbed into a single record. After dedup every Série A
season 2006-2022 has exactly 380 matches.

**Season boundaries.** The BR-Football file labels matches by calendar year,
but the COVID-delayed 2020 Série A/B/C and the 2020 Copa do Brasil final ran
into Jan-Mar 2021. Those records are re-attributed to the correct season by
matching them against the authoritative competition files (or by the
January/February heuristic for leagues only present in that file). As a
result, computed champions match history: Cruzeiro 2003 (100 pts),
Corinthians 2015, Palmeiras 2018, Flamengo 2019 (90 pts) and 2020,
Atlético-MG 2021, Palmeiras 2022 - including correct relegation zones.

**Known data quirks** (from the source files, documented for transparency):

- The 2023 Série A data comes only from BR-Football-Dataset (377 of 380
  matches) and its results do not fully match the real 2023 season, so
  computed 2023 standings differ from history.
- That file also contains one regional fixture (Brasilia FC x CA
  Taguatinga, Jan 2016) mislabeled as `Serie A`; standings filter out teams
  with fewer than half a season's matches, so tables are unaffected.
- The FIFA dataset has squads for only 16 Brazilian clubs (it is FIFA
  19-era): Flamengo, Palmeiras, Corinthians, São Paulo and Vasco have no
  squad. Queries for them return a helpful note listing available clubs.
- No scorer data exists in any dataset, so "top scorers" questions are
  answered from team goals only.
- Player ages/ratings reflect the FIFA 19-era snapshot (e.g. Neymar 92,
  Alisson 85 at Liverpool).

## Testing

BDD-style pytest suite (172 tests) following the spec's Gherkin scenarios:

```bash
pytest                              # full suite (~22 s)
pytest tests/test_bdd_match_queries.py -v
pytest --cov=brasil_mcp             # ~85% coverage
```

Coverage includes:

- `test_dates.py` / `test_normalize.py` - data-quality units (formats, name variants)
- `test_loaders.py` - all six CSVs load with the expected row counts; dedup verified (380 matches per Série A season)
- `test_bdd_match_queries.py` - the spec's match scenarios
- `test_bdd_team_queries.py` - statistics, comparisons, home records
- `test_bdd_player_queries.py` - FIFA search, club resolution, squads
- `test_bdd_competition_queries.py` - standings vs known history, brackets, coverage
- `test_bdd_statistics.py` - goals analysis, biggest wins, best records, derbies
- `test_bdd_sample_questions.py` - 28 sample questions from the spec, answered end-to-end
- `test_server.py` - MCP protocol integration over in-memory transport (initialize -> list_tools -> call_tool)
- `test_cli.py` - every CLI subcommand

Performance criteria from the spec are asserted: simple lookups < 2 s,
aggregate queries < 5 s (actual query times are milliseconds after the
~1.5 s one-time load).

## Data sources and licenses

| File | Source | License |
|------|--------|---------|
| `data/kaggle/Brasileirao_Matches.csv` | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `data/kaggle/Brazilian_Cup_Matches.csv` | same | CC BY 4.0 |
| `data/kaggle/Libertadores_Matches.csv` | same | CC BY 4.0 |
| `data/kaggle/BR-Football-Dataset.csv` | [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `data/kaggle/novo_campeonato_brasileiro.csv` | [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `data/kaggle/fifa_data.csv` | [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Demo/non-commercial use, as stated in the specification.
