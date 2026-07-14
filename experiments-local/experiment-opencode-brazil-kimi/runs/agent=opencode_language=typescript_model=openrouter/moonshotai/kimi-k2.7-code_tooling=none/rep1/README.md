# Brazilian Soccer MCP Server

A TypeScript [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that answers natural-language questions about Brazilian soccer using the provided Kaggle datasets.

## Features

The server exposes MCP tools for:

- **Match queries** – search matches by team(s), competition, season, date range, round, or stage.
- **Team queries** – win/draw/loss records, goals, home/away/both splits.
- **Head-to-head queries** – historical records between two teams.
- **Player queries** – search the FIFA player database by name, nationality, club, position, and rating.
- **Competition queries** – calculate season standings from match results.
- **Statistical analysis** – average goals, home win rate, biggest wins, best away records, top-scoring teams.

## Data

The following CSV files in `data/kaggle/` are loaded automatically:

- `Brasileirao_Matches.csv` – Brasileirão Série A matches
- `Brazilian_Cup_Matches.csv` – Copa do Brasil matches
- `Libertadores_Matches.csv` – Copa Libertadores matches
- `BR-Football-Dataset.csv` – extended match statistics
- `novo_campeonato_brasileiro.csv` – historical Brasileirão (2003–2019)
- `fifa_data.csv` – FIFA player database

Team names and dates are normalized across sources to handle the different conventions in each dataset.

## Install

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

The server communicates over stdio using the MCP protocol.

You can also override the data directory:

```bash
BRAZILIAN_SOCCER_DATA_DIR=/path/to/data npm start
```

## Test

```bash
npm test
```

Tests are written in a BDD style and cover normalizer utilities, CSV loading, query-engine functionality, response formatting, and the MCP server surface.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team(s), competition, season, date range, round, or stage |
| `get_team_record` | Get a team's record (wins/draws/losses/goals) |
| `get_head_to_head` | Get historical results between two teams |
| `search_players` | Search FIFA player data |
| `get_standings` | Calculate league standings for a competition/season |
| `get_statistics` | Compute aggregated statistics |
| `list_metadata` | List available competitions or seasons |
| `player_clubs_summary` | Summarise players and average ratings per club |

## License

See the data sources listed in `README.md` and `TASK.md` for dataset-specific licenses (CC BY 4.0, CC0, Apache 2.0).
