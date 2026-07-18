# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a queryable knowledge graph of Brazilian soccer data — matches, teams, players, and competitions — from the bundled Kaggle datasets. Any MCP-capable LLM client can connect and ask natural-language questions about Brazilian football.

Implements the specification in [`TASK.md`](./TASK.md) / [`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md).

## What was built

A TypeScript MCP server that loads all six provided CSV datasets once at startup into a normalized in-memory model and exposes 11 read-only MCP tools covering the spec's five required capability categories.

| Capability (spec) | Tools |
|---|---|
| Match Queries | `search_matches`, `last_match` |
| Team Queries | `team_stats`, `head_to_head` |
| Competition Queries | `standings`, `list_competitions` |
| Player Queries | `search_players`, `top_players`, `brazilian_players_at_brazilian_clubs` |
| Statistical Analysis | `match_statistics`, `biggest_wins` |

### Data model & normalization

- All five match files are parsed into a single `Match` shape with `source` provenance and a machine `competition` key, so queries can scope to a specific dataset or span them.
- The FIFA dataset is parsed into a `Player` shape (BOM-stripped; `+N` skill cells handled).
- **Team names are normalized for identity, not prettified to ambiguity.** The state suffix (`-RJ`, `-MG`, …) is *kept* on the canonical name, because `Atletico-MG`, `Atletico-GO` and `Atletico-PR` are three different clubs that would otherwise merge. The suffix is taken from the raw name or, when absent, from the state column (aligning the historical 2003-2019 file with the modern one). Long-form names (`Sport Club Corinthians Paulista` → `Corinthians`) and the `Atletico-PR`/`Athletico-PR` spelling split are unified via alias maps. Accents are folded for comparison, so a user asking for `Flamengo` matches the stored `Flamengo-RJ` and `São Paulo` matches `Sao Paulo-SP`.
- **Dates** handle all three dataset formats: ISO with time (`2012-05-19 18:30:00`), ISO date-only (`2023-09-24`), and Brazilian `DD/MM/YYYY` (`29/03/2003`). Unscheduled cells (`NA`, `-`) parse to `null` rather than throwing (e.g. the Libertadores unscored final row).

### Brazilian-clubs grouping

`brazilian_players_at_brazilian_clubs` matches the FIFA dataset's full official club names **exactly**, so Portuguese clubs that share a substring (`Sporting CP` vs `Sport Club do Recife`; `Vitória Guimarães` vs Brazilian `Vitória`) are never misclassified.

## Project layout

```
src/
  index.ts            # MCP server entrypoint (stdio transport)
  tools.ts            # 11 MCP tool definitions (zod schemas → query → format)
  data/
    types.ts          # Normalized Match / Player / Dataset model
    teams.ts          # Team-name normalization (identity + tolerant matching)
    dates.ts          # Multi-format date parsing & range checks
    loader.ts         # CSV parsing for all 6 files → normalized model
    query.ts          # Pure query/analysis engine (findMatches, standings, …)
    format.ts         # Human-readable response formatting
test/
  *.test.ts           # BDD (Given/When/Then) vitest scenarios
data/kaggle/          # The provided CSV datasets
```

## Usage

```bash
npm install        # install dependencies
npm run build      # compile to dist/
npm start          # run the MCP server over stdio
# or, for development:
npm run dev        # run via tsx without compiling
```

Connect with any MCP client (e.g. Claude Desktop) by pointing it at `node dist/index.js`.

### Example questions the server answers

- "Show me all Flamengo vs Fluminense matches" → `head_to_head`
- "What was Corinthians' record in 2019?" → `team_stats`
- "Who won the 2019 Brasileirão?" → `standings` (computes the table from results: Flamengo, 90 pts)
- "Who are the top Brazilian players?" → `top_players` (Neymar Jr, Casemiro, …)
- "What's the average goals per match in the Brasileirão?" → `match_statistics`
- "Show me the biggest wins" → `biggest_wins`

## Testing

BDD scenarios written as `Feature`/`Scenario` with Given/When/Then structure, run against the real datasets:

```bash
npm test           # vitest run (50 tests, ~1.3s)
npm run typecheck  # tsc --noEmit
```

Coverage: data loading (all 6 files), match queries (team/opponent/competition/season/date-range/stage, head-to-head symmetry), team queries (W/D/L, goals, points, Atletico-family disambiguation, standings ordering), player queries (nationality/club/rating, Portuguese-club false-positive guard), statistical analysis (averages, win rates, biggest-win margins), normalization & date parsing, and the MCP tool layer itself.

## Data sources & licenses

See [`README.md` source list above](#) and `TASK.md`. Datasets: Brasileirão Serie A, Copa do Brasil, Copa Libertadores, extended BR football stats, historical Brasileirão 2003-2019 (all CC BY 4.0 / CC0), and a FIFA player database (Apache 2.0). Data is bundled in `data/kaggle/` for offline use.
