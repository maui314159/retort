# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge graph interface over Brazilian soccer datasets, enabling natural language queries about players, teams, matches, and competitions.

## Overview

- **Use Case**: Demo / Non-commercial
- **Language**: TypeScript (ESM, Node.js)
- **Protocol**: MCP over stdio (JSON-RPC 2.0)
- **Data**: Six pre-downloaded Kaggle datasets (23,954 matches after dedup, 18,207 FIFA players)

## Data Sources

All datasets are in `data/kaggle/` and are loaded at server startup:

| File | Records | Source |
|------|---------|--------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Serie A (2012–2022) |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil (2012–2021) |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores (2013–2022) |
| `BR-Football-Dataset.csv` | 10,296 | Extended match statistics (multiple competitions) |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão (2003–2019) |
| `fifa_data.csv` | 18,207 | FIFA player database |

Overlapping matches between the brasileirao (2012–2022) and historical (2003–2019) datasets are automatically deduplicated by date + canonical team keys.

## Setup

```bash
npm install
npm run build
```

## Running the MCP Server

```bash
npm start          # or: node dist/index.js
```

The server communicates over stdio using the MCP protocol. Connect an MCP-compatible LLM client to query Brazilian soccer data.

## Tools Exposed

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, opponent, competition, season, date range, stage, or round |
| `team_statistics` | Win/loss/draw records, goals for/against, points (home/away/all, by season) |
| `head_to_head` | Compare two teams head-to-head across all matches |
| `search_players` | Search FIFA players by name, nationality, club, position, rating |
| `competition_standings` | Computed league table (3-points-for-a-win) for any competition/season |
| `goal_statistics` | Average goals per match, home/away/draw win rates, biggest victories |
| `best_record` | Top 5 teams by home or away record in a competition/season |
| `top_scoring_teams` | Teams ranked by total goals scored |
| `resolve_team` | Normalize a free-text team name to its canonical key |

## Team Name Normalization

The datasets use inconsistent team naming (`Palmeiras-SP`, `Flamengo - RJ`, `São Paulo`, `Sao Paulo`). The server normalizes all team names to canonical keys via de-accenting, suffix handling, and a curated alias table, so queries match across all files.

## Date Handling

Supports all three date formats in the datasets:
- ISO with time: `2012-05-19 18:30:00`
- ISO date only: `2023-09-24`
- Brazilian format: `29/03/2003`

## Testing

BDD-style tests (Given/When/Then) using Vitest:

```bash
npm test              # run all tests
npm run test:watch    # watch mode
npm run typecheck     # type-check only
```

Test coverage:
- **Match queries**: team/opponent search, season/competition/stage filtering, cross-file name matching
- **Team statistics**: wins/losses/draws, goals, home/away splits
- **Head-to-head**: aggregate records between two teams
- **Player queries**: nationality/club/position/rating filters, sorting
- **Competition standings**: computed league tables with correct sorting and goal difference
- **Goal statistics**: averages, win rates, biggest victories
- **Deduplication**: overlap removal between datasets
- **MCP tool layer**: schema validation, JSON serialization, dispatch
- **Real data loading**: all 6 CSV files load and query correctly

## Architecture

```
src/
├── index.ts       — MCP stdio server entrypoint
├── tools.ts       — MCP tool definitions + dispatcher (side-effect-free, unit-testable)
├── queries.ts     — query engine (pure functions over Dataset)
├── loader.ts      — CSV loading + normalization + deduplication
├── normalizer.ts  — team-name canonicalization
├── dates.ts       — multi-format date/number parsing
└── types.ts       — shared record types
```

## Smoke Test

```bash
node smoke.mjs      # end-to-end MCP stdio protocol test against real data
```

## License

Data licenses are per-source (CC BY 4.0, CC0, Apache 2.0) — see `README.md` data source links above. Code is provided for demo/non-commercial use.
