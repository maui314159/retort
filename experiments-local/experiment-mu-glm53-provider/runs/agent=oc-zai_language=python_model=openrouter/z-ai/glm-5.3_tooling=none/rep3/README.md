# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian soccer -- players, teams, matches and competitions -- from six
pre-downloaded Kaggle datasets. Implemented per the specification in
`brazilian-soccer-mcp-guide.md` / `TASK.md`.

## What was implemented

* **MCP server** (`server.py`) using the official `mcp` Python SDK (v2.x,
  stdio transport) exposing **20 tools** covering every required capability:
  match queries, team queries, player queries, competition queries and
  statistical analysis.
* **Normalized knowledge layer** (`soccer_mcp/`): all six CSV files are loaded
  into memory once (~1s), every team-name spelling is folded onto a canonical
  id, dates in ISO / ISO+time / Brazilian formats are parsed, and matches that
  exist in several files are deduplicated.
* **BDD test suite** (`tests/`): 113 pytest scenarios written in explicit
  Given/When/Then style (small harness in `soccer_mcp/bdd.py`), including
  end-to-end MCP protocol tests (in-memory client session + a real stdio
  subprocess boot), 32 sample-question coverage tests and performance tests.

## Quick start

```bash
source venv/bin/activate          # or: python -m venv venv && pip install -r requirements.txt
python server.py                  # runs the MCP server on stdio
```

Client configuration (Claude Desktop / any MCP client):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

Run the tests:

```bash
python -m pytest tests/
```

## Architecture

```
server.py                  MCP entry point (stdio); registers every tool
soccer_mcp/
  normalize.py             team-name canonicalization, competition/date parsing
  model.py                 dataclasses (Match, Player, TeamEntity, standings...)
  data_loader.py           CSV ingestion, team registry, dedup + source choice
  queries.py               pure analytical functions over the dataset
  formatting.py            renders answers in the spec's example formats
  tools.py                 the 20 MCP tools (thin wrappers)
  bdd.py                   Given/When/Then harness for the BDD suite
tests/                     BDD scenarios + MCP protocol tests
data/kaggle/               the six datasets (unchanged)
```

Design decisions worth knowing:

* **Team normalization.** Raw spellings are decomposed into
  `base + state/country` (e.g. `"América - MG"`, `"A.b.c. - RN"`,
  `"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"`,
  `"Nacional (URU)"`).  Bare spellings inherit their state when unambiguous
  ("Coritiba" -> PR); ambiguous famous clubs use a small hint table
  ("Flamengo" -> RJ, not PI); known renames fold (Athletico/Atlético-PR,
  Grêmio Prudente -> Barueri, Bragantino -> Red Bull Bragantino); foreign
  clubs that collide with small Brazilian clubs stay separate (River Plate vs
  River Plate-SE).  Genuinely ambiguous queries ("Atletico", "América")
  return a candidate list asking the user to disambiguate.
* **Duplicate coverage.** The same fixture appears in several files (Série A
  2012-2021 is in three of them).  Every (competition, season) is served from
  ONE default source chosen by priority with a completeness guard: a source
  keeps priority only when it holds >= 85% of the best source's playable
  matches for that season.  Consequences: Série A comes from
  `novo_campeonato_brasileiro.csv` (2003-2011), `Brasileirao_Matches.csv`
  (2012-2021) and `BR-Football-Dataset.csv` (2022-2023); Copa do Brasil 2021
  is served from `BR-Football-Dataset.csv` because the dedicated cup file has
  an unplayed round-of-16 with `NA` scores and no final.  A `source` parameter
  on `search_matches` can override this per query.
* **BR-Football season attribution.** That file has only dates, no season
  column.  Copa do Brasil editions start in Jan/Feb so calendar year = season;
  Série A/B/C matches in Jan-Mar are postponed spillover from the previous
  season (the COVID-affected 2020 season finished in Feb 2021) and roll back
  one year.
* **Tool errors are answers, not exceptions.** Unknown teams, ambiguous
  names, cup-vs-league mixups and unknown filters return helpful text so the
  connected LLM can recover.

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", matches by team/season/competition/stage/date range |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `last_match` | "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `compare_teams` | "Compare two teams side by side" |
| `best_records` | "Which team has the best away record?" (venue: overall/home/away) |
| `find_team` | resolve any name variant/nickname to the canonical team entity |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `list_teams` | teams in a competition/season or all Brazilian clubs |
| `search_players` | filter FIFA players by name/nationality/club/position/rating/age |
| `top_players` | "Who are the top Brazilian players?" (also by skill attribute) |
| `find_player` | "Who is Gabriel Barbosa?" |
| `list_competitions` | what the dataset covers, per competition |
| `standings` | computed league tables (Série A 2003-2023, B, C) with champion + relegation zone |
| `champion` | "Who won the 2019 Brasileirão?" / Libertadores / Copa do Brasil finals |
| `finals` | "Find all Copa do Brasil finals" |
| `knockout` | "Show the 2018 Copa Libertadores bracket" (aggregated two-legged ties) |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `derbies` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, ...) |

The `tests/test_sample_questions.py` file answers **32 sample questions**
through these tools (the spec requires >= 20).

## Data sources and licenses

Kaggle data can't be downloaded without an account so these (freely available
with attribution) datasets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## Data-quality notes (known limitations)

Honest limitations of the underlying data, all surfaced by the tools rather
than hidden:

* **Unscored rows are skipped and counted**: Brasileirao_Matches.csv has 82
  `NA` rows (the cancelled Chapecoense x Atlético-MG match after the 2016
  plane crash, and 81 unfilled 2022 round-29+ rows); Brazilian_Cup_Matches.csv
  has 16 (the unplayed 2021 round-of-16); Libertadores_Matches.csv has 2.
  Counts are reported in `SoccerData.data_quality`.
* **2022 Série A** falls back to BR-Football (379 of 380 matches);
  **2023 Série A** exists only in BR-Football with 377 of 380 matches, so
  computed 2023 tables are near-but-not-exact (e.g. Palmeiras shows 37 games).
* **Libertadores 2021 final is absent** and the **2022 final exists only as an
  unscored placeholder row** (Flamengo x Athletico), so `champion` cannot name
  those winners; `finals` reports the gap.
* **Shootouts are not recorded.** Finals level on aggregate (e.g. Copa do
  Brasil 2022, Corinthians x Flamengo) are reported as decided on penalties
  with no winner claimed.
* **FIFA player data is FIFA-19-era**: Brazilian club coverage is limited to
  the ~15 licensed clubs (Santos, Grêmio, Internacional, Cruzeiro, Bahia,
  Botafogo, Fluminense, ...).  Queries for unlicensed clubs (Flamengo,
  Corinthians, Palmeiras, São Paulo, Vasco) return zero players with an
  explanatory note; players like Gabriel Barbosa are simply absent.
* **2016 Série A**: the never-played Chapecoense x Atlético-MG match is
  recorded as a 0-0 draw in the historical file, so that source's table counts
  it (the dedicated file correctly omits it and is preferred for 2016).

## Testing

The suite uses BDD (Given/When/Then) scenarios per the spec's "Testing
Approach", executed as plain pytest via the tiny harness in
`soccer_mcp/bdd.py`:

```bash
python -m pytest tests/            # 113 scenarios (~5s)
```

Highlights:

* `test_match_queries.py` / `test_team_queries.py` /
  `test_player_queries.py` / `test_competition_queries.py` /
  `test_statistics.py` -- the spec's Gherkin scenarios (find matches between
  two teams, get team statistics) plus edge cases: dedup, name variants,
  ambiguity, unknown teams, source overrides.
* `test_mcp_server.py` -- in-memory MCP client session exercising the real
  protocol (tool listing, schema, calls) plus a stdio subprocess boot test.
* `test_sample_questions.py` -- 32 spec sample questions, each answered.
* `test_performance.py` -- simple lookups < 2s, aggregates < 5s, full load
  < 15s (all pass with large margins).
