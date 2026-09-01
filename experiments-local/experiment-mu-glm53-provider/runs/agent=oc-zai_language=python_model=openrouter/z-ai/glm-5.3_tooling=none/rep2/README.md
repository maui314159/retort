# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that answers natural-language questions
about Brazilian soccer — players, teams, matches, and competitions — over the
provided Kaggle datasets. Built in Python with the official `mcp` SDK (v2).

## Quick Start

```bash
# install (a virtualenv with Python 3.10+)
pip install -r requirements.txt

# run the MCP server (stdio transport, e.g. for Claude Desktop / opencode)
python main.py
```

Register it with an MCP client using this server config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["main.py"]
    }
  }
}
```

The data directory defaults to `data/kaggle/` and can be overridden with the
`BRAZILIAN_SOCCER_DATA_DIR` environment variable.

## Tools

18 tools are exposed over MCP, covering every capability category in the
specification:

| Category | Tools |
|----------|-------|
| Match queries | `search_matches` (by team, opponent, competition, season, date range, stage, home/away side), `last_match_between`, `derbies` |
| Team queries | `team_stats` (venue home/away/all), `best_records`, `team_competitions`, `team_profile` (cross-file: record + squad) |
| Player queries | `search_players` (name, club, nationality, position, rating bounds), `top_players`, `players_by_club` |
| Competition queries | `standings` (computed from results, with relegation zone), `champion`, `bracket` (knockout ties with aggregates), `competition_overview` |
| Statistics | `average_goals`, `biggest_wins`, `head_to_head`, `season_comparison` |

Team and competition names are matched leniently: `Palmeiras-SP`, `Palmeiras`
and `palmeiras` all work; `brasileirao`, `Serie A` and `copa do brasil` all
resolve; ambiguous names like `atletico` return the candidate list instead of
guessing. Dates accept `YYYY-MM-DD`, `DD/MM/YYYY`, ISO datetimes, or a bare
year in the date-range filters.

Example output (from `head_to_head`):

```
Flamengo vs Fluminense head-to-head (Fla-Flu):
- 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A)
- 2023-07-16: Fluminense 0-0 Flamengo (Brasileirão Série A)
...
Head-to-head in dataset: Flamengo 18 wins, Fluminense 15 wins, 13 draws
(46 matches, goals 63-52)
```

## Architecture

```
brazilian_soccer/
  normalize.py  # team-name canonicalization, aliases, date parsing, derby table
  models.py     # Match, Player, TeamRecord dataclasses
  data.py       # CSV loaders + Dataset (indexes, dedup, canonical source selection)
  query.py      # query engine (pure functions over Dataset)
  server.py     # MCPServer tools + response formatting
main.py         # stdio entry point
tests/          # BDD (Gherkin Given/When/Then) pytest suite
```

### Data integration notes

- **Overlapping sources.** Three files cover Série A with overlapping seasons
  (`Brasileirao_Matches.csv` 2012-2022, `novo_campeonato_brasileiro.csv`
  2003-2019, `BR-Football-Dataset.csv` 2014-2023). Match listings deduplicate
  cross-source copies of the same fixture; standings and statistics always
  use a single *canonical source* per (competition, season) — the source with
  the most scored matches that passes a round-robin sanity check. The check
  also rejects sources polluted by COVID-delayed 2020-season matches recorded
  under 2021 dates (real effect in `BR-Football-Dataset.csv`).
- **Team name variants.** Every raw name maps to a canonical key via
  accent-stripping, suffix handling (`-SP`, ` - RJ`, `(URU)`) and an alias
  table for full names (`Atlético Mineiro` → `Atlético-MG`,
  `Sport Club do Recife` → `Sport`). Clubs sharing a base stay distinct
  (`Atlético-MG`/`-PR`/`-GO`, `Botafogo-RJ`/`-SP`/`-PB`).
- **Cup finals.** Copa do Brasil round structure changed over the years, so
  finals are detected structurally per season (last round with ≤2 matches,
  etc.). Two-legged finals are aggregated; ties are reported as penalty
  decisions (penalty data is not in the datasets).
- **Honest reporting.** The FIFA dataset (FIFA 19) does not include every
  Brazilian club (no Flamengo/Palmeiras/Corinthians squads), so those queries
  return a graceful "no players found" message. The 2023 Série A table is
  computed from 377 of 380 matches with the count stated in the output.
- **Stages.** Libertadores stage labels (`quarterfinals`, `semifinals`, ...)
  are normalized; Brasileirão matches carry round numbers; the BR-Football
  source contributes corners/shots/attacks and half-time results as match
  extras.

## Testing

BDD scenarios written as Gherkin docstrings with Given/When/Then test names
(the approach requested by the specification):

```bash
venv/bin/python -m pytest tests/
# 151 passed
```

The suite covers all five capability categories, data-quality scenarios
(name variants, date formats, UTF-8, dedup), 28 end-to-end sample questions
from the specification (success criterion: ≥20), MCP protocol calls
(tool listing, `call_tool`, error handling), and the performance budget
(lookups < 2s, aggregates < 5s).

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

Demo/non-commercial use, per the specification.
