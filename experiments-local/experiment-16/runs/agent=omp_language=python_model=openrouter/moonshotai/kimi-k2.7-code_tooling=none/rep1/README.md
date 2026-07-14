# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions about Brazilian soccer using the Kaggle datasets included in this repository.

## What it does

The server loads six CSV datasets and exposes MCP tools for:

- **Match queries** — find matches by team, opponent, competition, season, date range, or venue.
- **Team statistics** — wins, draws, losses, goals scored/conceded, win rate, goal difference.
- **Head-to-head** — all matches between two teams plus a summary record.
- **Player queries** — search FIFA player data by name, nationality, club, position, or overall rating.
- **Competition queries** — calculated league standings, top scorers, relegated teams.
- **Statistical analysis** — average goals per match, biggest wins, home/away/draw splits.

## Project layout

```
.
├── data/kaggle/                # Provided CSV datasets
├── data_loader.py              # Loads and normalizes CSV data
├── query_engine.py             # Query functions over matches and players
├── server.py                   # MCP server entry point
├── tests/                      # pytest + pytest-bdd test suite
├── requirements.txt            # Runtime + test dependencies
└── pyproject.toml              # Package metadata
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the server

```bash
python server.py
```

The server uses `stdio` transport and can be connected to any MCP client (e.g., Claude Desktop, an MCP inspector, or a custom client).

## Available tools

- `find_matches(team, opponent, competition, season, date_from, date_to, venue, limit)`
- `team_statistics(team, competition, season, venue)`
- `head_to_head(team1, team2, competition, season)`
- `find_players(name, nationality, club, position, min_overall, limit)`
- `competition_standings(competition, season)`
- `biggest_wins(competition, season, limit)`
- `goals_summary(competition, season)`
- `top_scoring_teams(competition, season, limit)`
- `relegated_teams(season)`

## Running tests

```bash
pytest tests/ -v
```

The BDD scenarios live in `tests/features/brazilian_soccer.feature` and their step definitions are in `tests/test_brazilian_soccer.py`.

## Data notes

- Team names are normalized to handle state suffixes (`-SP`, `-RJ`), accents (`São Paulo` → `sao paulo`), and parenthetical country codes (`(URU)`).
- Dates are parsed from ISO (`2023-09-24`) and Brazilian (`29/03/2003`) formats.
- The FIFA player dataset bundled here contains only European clubs at the time of the FIFA 19 snapshot, so queries for Brazilian clubs return no players.

## Data sources and licenses

- [Brasileirão Matches](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) — CC BY 4.0
- [Brazilian Cup Matches](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) — CC BY 4.0
- [Libertadores Matches](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) — CC BY 4.0
- [BR-Football-Dataset](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) — CC0 Public Domain
- [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) — CC BY 4.0
- [FIFA Players Data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) — Apache 2.0
