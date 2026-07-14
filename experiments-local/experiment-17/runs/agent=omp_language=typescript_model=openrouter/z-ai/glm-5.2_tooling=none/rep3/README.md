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

## Implementation

A Model Context Protocol (MCP) server that exposes the Brazilian soccer datasets as a queryable knowledge graph. Built in TypeScript with the official `@modelcontextprotocol/sdk`, communicating over stdio.

### Architecture

```
src/
  types.ts             # Domain types: Match, Player, TeamStats, HeadToHead, StandingRow, AggregateStats, ClubSummary
  team-normalizer.ts   # Canonical team keys: strips state suffixes (-SP), country markers ((URU)), folds accents
  data-loader.ts       # CSV ingestion (csv-parse), date parsing (ISO + DD/MM/YYYY), BOM handling, cached normalization
  queries.ts           # Pure query functions: findMatches, headToHead, teamStats, standings, aggregateStats, biggestWins, findPlayers
  formatter.ts         # Human-readable answer formatting (match lists, tables, summaries)
  server.ts            # McpServer with 8 registered tools
  index.ts             # Entrypoint: binds the server to StdioServerTransport
tests/
  queries.test.ts      # BDD (Given/When/Then) scenarios over the real datasets
  server.test.ts       # End-to-end MCP protocol test via InMemoryTransport + Client
```

### MCP Tools

| Tool | Category | Description |
|------|----------|-------------|
| `search_matches` | Match Queries | Filter by team, opponent, competition, season, date range, venue |
| `head_to_head` | Team Queries | Win/draw/loss tally + recent matches between two teams |
| `team_stats` | Team Queries | Wins, draws, losses, goals, points, win rate (optionally by venue) |
| `standings` | Competition Queries | Computed league table for a competition season (3-1-0 points) |
| `aggregate_stats` | Statistical Analysis | Average goals, home/away/draw rates |
| `biggest_wins` | Statistical Analysis | Largest victories by goal difference |
| `search_players` | Player Queries | FIFA database search by name, nationality, club, position, rating |
| `brazilian_clubs_summary` | Player Queries | Brazilian players at Brazilian clubs: counts and average ratings |

### Team Name Normalization

The datasets use inconsistent naming (`Palmeiras-SP`, `Palmeiras`, `Nacional (URU)`, `Boavista Sport Club (antigo Esporte Clube Barreira) - RJ`). Every team name is reduced to a canonical accent-folded lowercase key, so cross-file queries match reliably. Display names keep the cleaned human-readable form.

### Build & Run

```bash
npm install
npm run build      # tsc -> dist/
npm start          # node dist/index.js  (MCP server over stdio)
```

### Test

```bash
npm test           # vitest run — 18 BDD scenarios
npm run test:watch
```

Tests load the real Kaggle datasets and assert: all 6 CSVs load, team-name variations collapse to one key, Flamengo–Fluminense matches resolve, Palmeiras 2023 stats are consistent, head-to-head tallies balance, standings sort by points, aggregate rates sum to 1.0, biggest wins order by goal difference, Brazilian players rank by overall, and the MCP server responds to tool calls end-to-end.

### Connecting an MCP Client

Point any MCP-compatible client at the server binary:

```json
{
  "mcpServers": {
    "brazilian-soccer": { "command": "node", "args": ["dist/index.js"] }
  }
}
```

Datasets load lazily on the first tool call and are cached for the process lifetime, so startup is fast and repeated queries are sub-second.
