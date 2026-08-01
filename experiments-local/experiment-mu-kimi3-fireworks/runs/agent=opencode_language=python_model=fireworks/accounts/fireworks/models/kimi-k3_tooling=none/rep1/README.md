# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
provides a knowledge-graph-style query interface over Brazilian soccer data:
Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores matches and a FIFA
player database. It answers natural-language questions about matches, teams,
players, competitions and statistics through 19 MCP tools.

Specification: [`TASK.md`](TASK.md) (a.k.a. `brazilian-soccer-mcp-guide.md`).

## Features

- **Match queries** — by team, opponent, competition, season, date range,
  venue and stage (finals, semifinals, group stage, ...), with derby detection
  (Fla-Flu, Gre-Nal, Majestoso, Choque-Rei, Ba-Vi, ...).
- **Team queries** — W/D/L records, goals for/against, win rates, home/away
  splits, competitions played.
- **Player queries** — name search, nationality/club/position filters, ratings
  and full skill profiles (18,207 FIFA players).
- **Competition queries** — league standings calculated from match results
  (3-1-0 points, CBF tie-breakers, champion/relegation flags).
- **Statistical analysis** — goals averages, home/draw/away splits, biggest
  wins, best home/away records, season comparisons.

Data-quality handling per the spec: team-name normalization across the five
different naming conventions in the source files (`Palmeiras-SP`,
`América - MG`, `Athletico-PR`, `Vasco Da Gama RJ`,
`Sport Club Corinthians Paulista`), ISO/Brazilian/datetime date parsing, and
UTF-8 accents (São Paulo, Grêmio, Avaí).

## Architecture

```
server.py                  # stdio entry point: python server.py
soccer_mcp/
  normalize.py             # team/competition/date normalization + derby table
  data.py                  # DataStore: loads the 6 CSVs into a unified,
                           # deduplicated match table + FIFA player table
  queries.py               # structured query layer (dicts in, dicts out)
  formatting.py            # text rendering per the spec's answer formats
  tools_api.py             # flat string-returning functions (unit-testable)
  mcp_server.py            # FastMCP wiring: 19 registered tools
tests/
  test_normalize.py        # unit tests
  test_data.py             # loading/dedupe/coverage tests
  test_queries.py          # query-layer tests
  test_mcp_server.py       # in-memory FastMCP client integration tests
  test_sample_questions.py # 24 sample questions from the spec
  features/*.feature       # Gherkin BDD scenarios (pytest-bdd)
  bdd/test_*.py            # step definitions
```

### Data notes

The five match files overlap (e.g. the 2019 Brasileirão appears in three of
them), so the store deduplicates fixtures by
`(competition, season, home, away)` in source-priority order — date keys are
unreliable because sources disagree by ±1 day on late kick-offs, and scores
occasionally conflict. Other curated fixes:

- COVID-19 overflow: 2020-season matches played in early 2021 are reassigned
  to season 2020.
- The cancelled 2016 round-38 Chapecoense–Atlético-MG fixture (LaMia Flight
  2933) is removed — one source records a phantom 0-0.
- A mislabeled state-championship row in BR-Football ("Serie A" Brasília FC
  vs CA Taguatinga) is dropped via roster validation.
- Copa do Brasil round numbers are mapped to stage labels relative to each
  season's final round.

Ground-truth check: the calculated 2019 Série A standings reproduce reality
exactly — Flamengo champions with 90 pts (28W 6D 4L); Cruzeiro, CSA,
Chapecoense and Avaí relegated.

## Usage

Requires Python 3.10+ and `pip install -r requirements.txt`.

Run the MCP server over stdio:

```bash
python server.py
```

Or wire it into an MCP client (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

Set `SOCCER_DATA_DIR` to override the default `data/kaggle` location.

### Tools

`dataset_summary`, `list_competitions`, `list_teams`, `search_matches`,
`head_to_head`, `last_match`, `find_derbies`, `team_stats`,
`team_competitions`, `standings`, `top_scoring_teams`, `competition_stats`,
`biggest_wins`, `best_home_records`, `best_away_records`, `compare_seasons`,
`search_players`, `top_players`, `player_profile`.

## Testing

```bash
python -m pytest            # full suite: unit + BDD + MCP integration
```

216 tests: unit tests for normalization/data/queries, Gherkin BDD scenarios
(pytest-bdd, Given/When/Then per the spec), in-memory FastMCP client
integration tests, and the 24 sample questions from the specification.

Query performance (after a one-time ~0.6s data load): simple lookups
1–20 ms, aggregates 2–7 ms — well under the 2 s / 5 s limits.

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
