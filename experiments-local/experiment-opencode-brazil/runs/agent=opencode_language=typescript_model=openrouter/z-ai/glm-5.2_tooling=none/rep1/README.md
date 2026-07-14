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

## Implementation

This repository implements the Brazilian Soccer MCP Server specified in `TASK.md` /
`brazilian-soccer-mcp-guide.md` in TypeScript.

### Stack
- **Language:** TypeScript (ESM, Node 20+)
- **MCP SDK:** `@modelcontextprotocol/sdk` (stdio transport)
- **CSV parsing:** `csv-parse`
- **Schema validation:** `zod`
- **Tests:** `node:test` with BDD Given/When/Then scenarios

### Project layout
```
src/
  types.ts       shared domain types (NormalizedMatch, PlayerRecord, ...)
  normalize.ts   team-name canonicalization, multi-format date parsing
  loaders.ts     CSV loaders for all 6 datasets (cached)
  queries.ts     filterMatches, computeTeamStats, headToHead, standings,
                 biggestWins, averageGoals, filterPlayers, ...
  format.ts      natural-language response formatters (spec's example formats)
  tools.ts       MCP tool registrations (11 tools)
  server.ts      stdio transport wiring
  index.ts       CLI entrypoint
tests/
  bdd.test.ts    BDD scenarios covering all 5 query categories + data quality
```

### Build & test
```bash
npm install
npm run build        # tsc -> dist/
npm test             # node --test dist/tests/*.test.js
npm run typecheck    # tsc --noEmit
npm start            # run the stdio MCP server
```

### MCP tools exposed
`find_matches`, `get_team_statistics`, `head_to_head`, `last_match_between`,
`standings`, `biggest_wins`, `average_goals`, `search_players`, `club_roster`,
`list_competitions`, `list_teams`.

### Data handling
- Team names are canonicalized (state suffixes like `-SP`, accented variants
  like `São Paulo`/`Grêmio`, full names like `Sport Club Corinthians Paulista`,
  and `(antigo ...)` qualifiers all collapse to a single form).
- Dates are parsed from ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`),
  and Brazilian (`29/03/2003`) formats.
- All 6 CSV files are loaded lazily and cached; cross-file queries (e.g.
  player + match data) are supported.

### Overriding the data directory
Set `BRAZILIAN_SOCCER_DATA_DIR` to point the server at a different copy of the
Kaggle datasets (defaults to `data/kaggle`).

- data/kaggle/fifa_data.csv
