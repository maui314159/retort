# Brazilian Soccer MCP Server

A TypeScript [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes Brazilian soccer data from the included Kaggle datasets as queryable tools.

## Specification

The full requirements are in [TASK.md](./TASK.md) and [brazilian-soccer-mcp-guide.md](./brazilian-soccer-mcp-guide.md).

## Features

- Loads and normalizes all 6 provided CSV files from `data/kaggle/`.
- Handles team-name variations, state suffixes, multiple date formats, and UTF-8 text.
- Exposes MCP tools for:
  - **Match queries** — by team, head-to-head, competition, season, date range, and round.
  - **Team queries** — win/loss/draw records, goals, win rate, home/away splits.
  - **Player queries** — by name, nationality, club, position, and FIFA overall rating.
  - **Competition queries** — calculated league standings and aggregate statistics.
  - **Statistical analysis** — biggest wins, average goals, home/away/draw win rates, best away records.

## Project Structure

```
.
├── src/
│   ├── data.ts      # CSV loading, normalization, and repository types
│   ├── queries.ts   # Query/analysis functions and formatting
│   ├── server.ts    # MCP server and tool definitions
│   └── index.ts     # CLI entry point
├── tests/
│   └── soccer.test.ts  # BDD-style tests
├── data/kaggle/     # Provided CSV datasets
├── package.json
├── tsconfig.json
└── jest.config.cjs
```

## Setup

```bash
npm install
npm run build
```

## Usage

### Run the MCP server

```bash
npm start
```

The server communicates over stdio and can be connected to any MCP client.

### Available Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Search matches by team, competition, season, date range, round |
| `team_statistics` | Team record, goals, and win rate |
| `head_to_head` | Compare two teams across all matches |
| `search_players` | Search FIFA player database by name/nationality/club/position |
| `competition_standings` | Calculate league table from match results |
| `competition_statistics` | Aggregate stats and biggest wins |
| `best_away_record` | Teams with the best away records |

## Testing

```bash
npm test
```

Tests are written in a BDD style and cover data loading, match/team/player/competition queries, MCP tool invocation, and output formatting.

## Data Sources

Kaggle datasets (freely available with attribution) included in `data/kaggle/`:

- [Jogos do Campeonato Brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) (CC BY 4.0)
- [Brazilian Football Matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) (CC0 Public Domain)
- [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) (CC BY 4.0)
- [FIFA Players Data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) (Apache 2.0)
