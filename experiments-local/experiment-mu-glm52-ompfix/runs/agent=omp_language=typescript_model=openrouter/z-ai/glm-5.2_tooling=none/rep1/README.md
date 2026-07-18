# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph-style
interface over Brazilian soccer datasets — matches, teams, players, and
competitions — so an LLM client can answer natural-language questions about
Brazilian football.

Implements the specification in [`TASK.md`](./TASK.md) /
[`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md).

## What it does

Loads six Kaggle CSV datasets (Brasileirão, Copa do Brasil, Libertadores,
extended BR-Football stats, historical Brasileirão 2003–2019, and the FIFA
player database) into normalised in-memory structures and answers structured
queries through twelve MCP tools:

| Tool | Purpose |
|------|---------|
| `find_matches` | Filter matches by team / opponent / competition / season / date range |
| `last_match_between` | Most recent fixture between two teams with score |
| `team_stats` | W/D/L record, goals, home/away split (optionally per season) |
| `head_to_head` | Pairwise record + recent match list |
| `competitions_for_team` | Distinct competitions a team appears in |
| `player_search` | FIFA player filter (name / nationality / club / position) |
| `top_brazilian_players` | Highest-rated Brazilians |
| `brazilian_players_by_club` | Brazilians grouped by club (count + avg rating) |
| `standings` | Computed league table (3-1-0 points) for a competition+season |
| `biggest_wins` | Largest goal-difference victories |
| `average_goals` | Mean goals/match + home/away/draw rates |
| `best_record_at_venue` | Team with the best home (or away) record |

## Design

- **`src/types.ts`** — domain types (`MatchRecord`, `PlayerRecord`, standings, H2H).
- **`src/normalize.ts`** — tolerant team-name and date normalisation so
  `Palmeiras-SP`, `América - MG`, `Nacional (URU)` and `São Paulo` all match
  across datasets; ISO / ISO+time / `DD/MM/YYYY` dates; accent-folded keys.
- **`src/loaders.ts`** — one loader per CSV, mapping source columns into the
  canonical shapes; total (never throws on a bad row) and BOM-tolerant.
- **`src/engine.ts`** — `SoccerDatabase` query engine backing every tool.
- **`src/format.ts`** — pure formatters producing the TASK.md answer formats.
- **`src/index.ts`** — `McpServer` over stdio transport + `buildServer` / `loadDatabase` exports.

Every code file opens with a context block comment describing the project,
purpose, datasets, and module role.

## Build & run

```bash
npm install
npm run build      # tsc → dist/
node dist/index.js # stdio MCP server
```

Connect from any MCP client (Claude Desktop, etc.) by pointing its stdio
transport at `node /path/to/dist/index.js`.

## Test

BDD-style (Given/When/Then) scenarios with Vitest:

```bash
npm test
```

49 tests across four suites:

- `tests/normalize.test.ts` — team-name & date normalisation (19)
- `tests/format.test.ts` — response formatting (9)
- `tests/engine.test.ts` — query engine over the real datasets (20)
- `tests/server.test.ts` — live stdio MCP handshake + tool call (1)

## Data

Pre-downloaded Kaggle datasets in `data/kaggle/` (see `TASK.md` for schemas &
licenses). The Brasileirão match file covers seasons 2012–2022; the FIFA
player snapshot is European-focused but contains 827 Brazilian players,
including Santos FC.

## License

MIT (code). Datasets retain their upstream Kaggle licenses (CC BY 4.0 / CC0 / Apache 2.0).
