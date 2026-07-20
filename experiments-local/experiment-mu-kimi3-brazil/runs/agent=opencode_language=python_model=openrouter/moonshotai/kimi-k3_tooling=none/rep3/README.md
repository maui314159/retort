# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

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

---

## Implementation

An MCP (Model Context Protocol) server providing a knowledge-graph style
interface to the datasets above, implemented per `TASK.md`:

| File | Purpose |
|------|---------|
| `soccer_data.py` | Loads all six CSVs into a unified in-memory store. Normalises team names (accents, `-SP`/` - MG` state suffixes, `(URU)` country tags, alias variants like `Atletico-PR`/`Athletico Paranaense`), parses ISO/BR date formats, and de-duplicates fixtures that appear in more than one file (3-day date window). |
| `query_engine.py` | Query functions for the five required categories: match queries, team queries, player queries, competition queries (standings calculated from results) and statistical analysis. |
| `server.py` | FastMCP server (stdio transport) exposing 13 tools. |
| `tests/` | BDD test suite (pytest-bdd): Gherkin feature files + step definitions covering all query categories, data-quality rules, cross-file queries and the performance criteria. |

### MCP tools

`find_matches`, `head_to_head`, `team_statistics`, `list_teams`,
`search_players`, `top_players`, `player_profile`,
`competition_standings`, `top_scoring_teams`, `list_competitions`,
`biggest_wins`, `best_team_records`, `competition_overview`

### Run

```bash
pip install -r requirements.txt
python server.py          # starts the MCP server on stdio
```

### Test

```bash
python -m pytest          # 34 BDD scenarios (Given/When/Then)
```

### Notes

- All six CSV files are queryable; fixtures shared between files
  (e.g. Brasileirão 2012-2019 appears in three sources) are merged, so
  calculated standings are exact (Série A seasons: 380 matches, 20 teams
  x 38 rounds; Flamengo champion 2019 with 90 pts).
- Simple lookups answer in milliseconds; aggregates well under 5 s.
