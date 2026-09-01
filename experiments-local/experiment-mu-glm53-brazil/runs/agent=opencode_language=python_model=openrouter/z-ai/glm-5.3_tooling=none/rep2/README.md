# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md (see also TASK.md)

## What was implemented

A Python MCP (Model Context Protocol) server that exposes the bundled
Kaggle datasets as query tools for an LLM:

- `brazilian_soccer_mcp/normalize.py` — team-name canonicalization and
  date/value parsing. Handles the naming variations in the sources
  ("Palmeiras-SP" vs "Palmeiras" vs "Sport Club Corinthians Paulista",
  "Atletico Mineiro", "Athletico"), state suffixes, country codes
  ("Nacional-URU", "Guaraní (PAR)"), accents and several date formats
  (ISO, ISO+time, DD/MM/YYYY).
- `brazilian_soccer_mcp/models.py` — `Match`, `Player`, `TeamRecord`.
- `brazilian_soccer_mcp/loaders.py` — loaders for all six CSV files.
- `brazilian_soccer_mcp/service.py` — the query engine: match search,
  head-to-head, team statistics, standings, derbies, biggest wins, league
  statistics, best home/away records and player queries. Because three
  files overlap (the same Brasileirão/Copa do Brasil fixtures appear with
  different dates), one preferred source is chosen per (competition,
  season) so every fixture appears exactly once; `source` parameters can
  override this to reach the extended corner/shot/attack statistics.
- `brazilian_soccer_mcp/server.py` — the MCP server (15 tools, stdio
  transport) built on the official `mcp` Python SDK.
- `run_server.py` — server entry point.

### MCP tools

`search_matches`, `head_to_head`, `team_stats`, `team_competitions`,
`list_teams`, `resolve_team`, `standings`, `competition_info`,
`derby_matches`, `biggest_wins`, `league_statistics`, `best_records`,
`search_players`, `top_players`, `players_by_club`.

## Running

```bash
pip install -r requirements.txt
python run_server.py                 # stdio MCP server
python run_server.py --data-dir data/kaggle
```

Example client configuration (Claude Desktop / any MCP client):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/path/to/run_server.py"]
    }
  }
}
```

## Testing

BDD (Gherkin + pytest-bdd) scenarios in `tests/features/` plus unit,
loader, in-process MCP-protocol, performance and sample-question tests:

```bash
python -m pytest
```

116 tests cover:

- all six CSV files load with the documented row counts
- match/team/player/competition/statistical queries (Gherkin scenarios)
- name variation handling and ambiguity reporting
- standings computed from matches (2019 Brasileirão: Flamengo 90 pts,
  28W-6D-4L, matching the spec's expected answer)
- at least 20 sample questions from the specification answered end-to-end
- the MCP protocol surface (tool listing + tool calls) over in-memory
  streams
- the spec's performance budgets (simple lookups < 2s, aggregates < 5s)

## Data caveats

- The FIFA dataset (FIFA 18-era) contains licensed squads for only 16
  Brazilian clubs; queries for unlicensed clubs such as Flamengo or
  Corinthians return empty results.
- The Brasileirão 2022 rows are missing four late-season scores; records
  count only matches with results.
- The 2023 Serie A comes from the BR-Football dataset (377 of 380
  matches), so its table is close but not exact.

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
