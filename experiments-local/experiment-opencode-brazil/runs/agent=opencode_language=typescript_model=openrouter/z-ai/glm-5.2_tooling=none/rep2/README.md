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

A TypeScript MCP (Model Context Protocol) server exposing a knowledge-graph
interface over the datasets above. Implemented per `TASK.md` /
`brazilian-soccer-mcp-guide.md`.

### Stack
- TypeScript (NodeNext ESM), strict mode
- `@modelcontextprotocol/sdk` for the MCP server (stdio transport)
- `papaparse` for CSV parsing
- `zod` for tool argument schemas
- `vitest` for BDD-style tests (Given/When/Then)

### Project layout
```
src/
  types.ts       # domain types (Match, Player, TeamRecord, ...)
  normalize.ts   # team-name & date normalization, TeamNameRegistry
  loader.ts      # two-pass CSV loader (all 6 files) -> Dataset
  query.ts       # query engine (matches, teams, players, competitions, stats)
  format.ts      # plain-text result formatters
  server.ts      # MCP server + 13 registered tools
  index.ts       # entry point (stdio)
test/
  bdd.ts         # Given/When/Then helpers
  fixtures.ts    # shared dataset loader
  *.test.ts      # BDD specs for each capability category
```

### Build & test
```bash
npm install
npm run build        # tsc -> dist/
npm run typecheck    # tsc --noEmit (includes tests)
npm test             # vitest run
npm start            # node dist/index.js  (MCP over stdio)
```

The data directory defaults to `./data/kaggle`; override with the
`BR_SOCCER_DATA_DIR` environment variable.

### MCP tools
`search_matches`, `head_to_head`, `team_stats`, `search_players`,
`top_players`, `standings`, `champion`, `relegated`, `competition_stats`,
`biggest_wins`, `list_competitions`, `list_teams`, `list_seasons`.

### Data-quality handling
- **Team name variations**: a `TeamNameRegistry` scans the whole dataset and
  keeps the `-UF` state suffix only when the base name is ambiguous (e.g.
  `Atletico-MG` vs `Atletico-PR` are kept distinct, while `Palmeiras-SP`
  normalizes to `Palmeiras`). Matching is accent- and case-insensitive with
  substring fallback.
- **Date formats**: ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`),
  Brazilian (`29/03/2003`), and dotted (`2003.03.29`) are all parsed to
  `YYYY-MM-DD`.
- **Character encoding**: UTF-8 throughout (São Paulo, Grêmio, Avaí).

### Tests
58 BDD specs across 8 files cover all five capability categories (match,
team, player, competition, statistical), the loader, normalization, and the
MCP server tool layer (using an in-memory transport). The real Kaggle
datasets are loaded for the data-backed specs.

