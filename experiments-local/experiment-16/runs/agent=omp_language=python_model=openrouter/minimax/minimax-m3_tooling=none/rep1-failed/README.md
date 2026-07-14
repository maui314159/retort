# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that
answers natural-language questions about Brazilian soccer using the
Kaggle datasets bundled in this repository.

## What it does

The server loads six CSV datasets, normalizes team names and dates
across them, deduplicates matches that show up in more than one
source, and exposes the following MCP tools to any connected LLM
client:

* **Match queries** — find matches by team, opponent, competition,
  season, date range, or venue.
* **Team statistics** — per-team wins, draws, losses, goals for /
  against, win rate, and goal difference.
* **Head-to-head** — every match between two teams plus a summary
  record.
* **Player queries** — search the FIFA 19 player dataset by name,
  nationality, club, position, minimum overall rating, or maximum age.
* **Competition queries** — calculated league standings and the
  bottom four teams of a Brasileirão season.
* **Statistical analysis** — average goals per match, biggest wins,
  home/away/draw splits, top scoring teams.
* **Auxiliary helpers** — team competition history, counts of
  Brazilian players at Brazilian clubs, and a `raw_query` escape
  hatch that lets a client invoke any tool by name and receive
  structured JSON.

The server speaks MCP over **stdio** and can be wired up to any
MCP-compatible client (Claude Desktop, an MCP inspector, or a custom
client).

## Project layout

```
.
├── data/
│   └── kaggle/                 # Provided CSV datasets (6 files)
├── data_loader.py              # CSV ingestion + team/date normalization
├── query_engine.py             # High-level query functions
├── server.py                   # MCP server entry point (FastMCP)
├── tests/
│   ├── features/
│   │   └── brazilian_soccer.feature
│   ├── test_brazilian_soccer.py    # pytest-bdd step definitions
│   ├── test_data_loader.py         # Normalization + loading unit tests
│   ├── test_query_engine.py        # Query engine unit tests
│   └── test_server.py              # Server tool wrapper unit tests
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Installation

```bash
# Runtime dependencies only:
pip install -r requirements.txt

# Or with the dev/test extras:
pip install -r requirements-dev.txt
```

The server requires Python 3.10 or later and depends on
[`mcp>=1.0.0`](https://pypi.org/project/mcp/) and
[`pandas>=2.0.0`](https://pypi.org/project/pandas/).

## Running the server

```bash
python server.py
```

The server uses stdio transport. To exercise it from the CLI you can
drive it with any MCP-compatible client.

## Available tools

| Tool                       | What it returns                                                |
|----------------------------|----------------------------------------------------------------|
| `find_matches`             | Matches matching team / opponent / competition / season / date |
| `team_statistics`          | Wins, draws, losses, goals, win rate for one team              |
| `head_to_head`             | All matches between two teams plus a summary record            |
| `find_players`             | FIFA players matching the given filters                        |
| `competition_standings`    | Calculated league standings (points, W/D/L, GD)                |
| `biggest_wins`             | Matches ordered by largest goal difference                     |
| `goals_summary`            | Average goals per match + home/away/draw splits                |
| `top_scoring_teams`        | Teams ranked by total goals scored                             |
| `relegated_teams`          | The bottom four teams of a Brasileirão season                  |
| `team_competition_history` | Which competitions a team has played in                       |
| `brazilian_club_summary`   | Counts of Brazilian players at Brazilian clubs                 |
| `raw_query`                | Escape hatch that returns structured JSON for any tool         |

## Sample prompts

Some questions the server can answer:

- *"Show me all Flamengo vs Fluminense matches in 2023"*
- *"What is Corinthians' home record in 2022?"*
- *"Who won the 2019 Brasileirão?"* — returns the 2019 standings,
  with Flamengo first on 90 points.
- *"Which teams were relegated in 2019?"*
- *"Find all Brazilian players in the dataset"*
- *"What competitions has Palmeiras played in?"*
- *"What was the average goals per match in the 2023 Brasileirão?"*

## Running the tests

```bash
pytest tests/ -v
```

The suite combines:

* `test_data_loader.py` — normalization, parsing, deduplication.
* `test_query_engine.py` — every public query function.
* `test_server.py` — every MCP tool wrapper.
* `test_brazilian_soccer.py` — Gherkin-style BDD scenarios backed
  by `tests/features/brazilian_soccer.feature`.

All 91 tests pass against the bundled data.

## Data notes

* **Team name normalization** — state suffixes (`-SP`, `-RJ`),
  country codes (`(URU)`, `-EQU`), and accents are all folded into a
  single canonical key (`Flamengo-RJ` → `flamengo`,
  `Atletico-PR` → `athletico paranaense`).  A pre-strip alias map
  preserves state-suffix disambiguation (e.g. `Atletico-PR` vs
  `Atletico-MG`) that would otherwise be lost when the suffix is
  stripped.
* **Date parsing** — ISO (`2023-09-24`), ISO with time
  (`2023-09-24 18:30:00`), and Brazilian (`29/03/2003`) formats are
  all handled.
* **Deduplication** — `brasileirao`, `novo_brasileirao`, and
  `br_football` overlap for 2014-2019.  Within each
  `(competition, season, team-pair)` group, matches that occur
  within 7 days of each other are clustered together and the
  highest-priority source (BR-Football > Brasileirao > novo_brasileirao)
  is kept.  Home and away legs of the same fixture are always
  months apart, so a 7-day window reliably separates duplicates
  from genuine rematches.
* **Player coverage** — the bundled FIFA 19 snapshot does not
  contain players for several major Brazilian clubs (Flamengo,
  Palmeiras, Corinthians, São Paulo, etc.); only Santos,
  Atlético Mineiro, Grêmio, Internacional, Botafogo, Fluminense,
  Cruzeiro, and Athletico-PR have Brazilian-club players in the
  dataset.

## Data sources and licenses

| File                                       | Source                                                                                                                                  | License            |
|--------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|--------------------|
| `Brasileirao_Matches.csv`                  | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)                       | CC BY 4.0          |
| `Brazilian_Cup_Matches.csv`                | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)                       | CC BY 4.0          |
| `Libertadores_Matches.csv`                 | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)                       | CC BY 4.0          |
| `BR-Football-Dataset.csv`                  | [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)                                     | CC0 (Public Domain)|
| `novo_campeonato_brasileiro.csv`           | [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)                     | CC BY 4.0          |
| `fifa_data.csv`                            | [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)                                                 | Apache 2.0         |
