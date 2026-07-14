# Brazilian Soccer MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that
provides a knowledge-graph-style interface for Brazilian football data.  It
loads six Kaggle datasets and exposes tools for querying matches, teams,
players, competitions and statistics using natural-language-friendly
parameters.

## What was done

- Implemented a Python MCP server using the official MCP Python SDK and
  FastMCP.
- Built a unified data loader that reads and normalizes all six CSV files
  under `data/kaggle/`.
- Added team-name normalization so that variations like `Palmeiras`,
  `Palmeiras-SP` and `Sociedade Esportiva Palmeiras` all resolve to the same
  canonical team.
- Added multi-format date parsing (ISO, Brazilian `DD/MM/YYYY`, datetime
  strings) and UTF-8 handling for Portuguese text and accents.
- Implemented query tools for:
  - Match search (team, opponent, date range, competition, season)
  - Head-to-head records
  - Team statistics (overall/home/away, by season/competition)
  - Player search and top Brazilian players
  - Competition standings and winners
  - Aggregate statistics (average goals, biggest wins, top-scoring teams,
    season comparison)
- Wrote BDD-style tests with `pytest-bdd` covering matches, teams, players,
  competitions and statistics.

## Project structure

```text
.
├── brazilian_soccer_mcp/
│   ├── __init__.py
│   ├── team_normalizer.py   # canonical team-name mapping
│   ├── data_store.py        # CSV loading and normalization
│   ├── queries.py           # query engine
│   └── server.py            # FastMCP server / tools
├── tests/
│   ├── conftest.py
│   ├── features/            # Gherkin feature files
│   └── step_defs/           # pytest-bdd step definitions
├── data/kaggle/             # provided datasets
├── pyproject.toml
└── README.md
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the server

```bash
python -m brazilian_soccer_mcp.server
# or, after installation:
brazilian-soccer-mcp
```

The server uses stdio transport and can be connected to any MCP client.

## Running tests

```bash
pytest
```

## Available tools

| Tool | Purpose |
|------|---------|
| `brazilian_soccer_find_matches` | Search matches by team, opponent, date range, competition, season |
| `brazilian_soccer_head_to_head` | Historical record between two teams |
| `brazilian_soccer_team_stats` | Wins/draws/losses/goals/win rate |
| `brazilian_soccer_list_teams` | All canonical team names |
| `brazilian_soccer_search_players` | Search FIFA player data by name, nationality, club, position, rating |
| `brazilian_soccer_top_brazilian_players` | Highest-rated Brazilian players |
| `brazilian_soccer_standings` | League table for a season |
| `brazilian_soccer_competition_winner` | Team with the most points in a season |
| `brazilian_soccer_biggest_wins` | Largest-margin victories |
| `brazilian_soccer_average_goals` | Average goals and home win rate |
| `brazilian_soccer_top_scorers` | Teams with the most goals scored |
| `brazilian_soccer_compare_seasons` | Compare aggregate stats across seasons |

## Data sources

All datasets are included in `data/kaggle/` and retain their original licenses.
See the specification document (`brazilian-soccer-mcp-guide.md` / `TASK.md`)
for attribution and column descriptions.
