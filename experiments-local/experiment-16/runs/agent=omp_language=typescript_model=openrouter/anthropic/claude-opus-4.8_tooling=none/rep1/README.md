# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes
a natural-language-friendly query interface over Brazilian soccer datasets
(matches, teams, competitions and FIFA players). Written in TypeScript, it loads
the six provided Kaggle CSVs into an in-memory store and answers match, team,
player, competition and statistical queries through MCP tools.

Specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(identical to `TASK.md`).

## What was implemented

- **Dependency-free CSV ingestion** (`src/csv.ts`) handling quoted fields,
  escaped quotes, embedded commas, a UTF-8 BOM (`fifa_data.csv`) and CRLF/LF.
- **Name & date normalization** (`src/normalize.ts`):
  - Accent/cedilla folding ("São Paulo" → "sao paulo", "Grêmio" → "gremio").
  - Team canonicalization that **keeps the state token** so same-named,
    different-state clubs never collapse (Atlético-**MG** vs Atlético-**GO** vs
    Athletico-**PR** stay distinct), strips country qualifiers ("Nacional (URU)"
    → "nacional") and club noise words ("São Paulo FC" → "sao paulo").
  - Multi-format date parsing: ISO (`2023-09-24`), ISO datetime
    (`2012-05-19 18:30:00`) and Brazilian `DD/MM/YYYY` (`29/03/2003`).
  - Tolerant goal parsing (`"2"`, `"2.0"`, `""`, `"NA"`).
- **Unified data store** (`src/store.ts`) projecting all five match files and the
  FIFA player file into single `Match` / `Player` shapes. The same season exists
  in up to three overlapping files, so the loader **deduplicates per
  `(competition, season)`**, keeping the single most complete source — this is
  what makes standings, head-to-head and goal averages accurate instead of
  double/triple counted.
- **Pure query layer** (`src/queries.ts`): match search (team/opponent/side/
  competition/season/date-range), team stats (overall + home/away split),
  head-to-head, league standings (3-1-0 points, CBF tiebreaker
  points→wins→GD→GF), player search, goals-per-match aggregates and biggest
  wins. UF-aware team matching lets a plain query ("Palmeiras") match a
  state-suffixed key ("palmeiras sp") while keeping "Santos" from matching the
  Mexican "Santos Laguna".
- **MCP server** (`src/server.ts`, `src/index.ts`) exposing eight tools over
  stdio, each returning both formatted text (for LLM clients) and structured
  JSON (for programmatic clients).

### Validated results (from the provided data)

- 2019 Brasileirão computed champion: **Flamengo, 90 pts (28W 6D 4L)** — matches
  the spec example; Santos placed above Palmeiras on the wins tiebreaker at 74
  pts each.
- Average goals per match (Brasileirão): **2.57**; home win rate **49.7%**.
- 16,826 deduplicated matches and 18,207 players loaded.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, side, competition, season, date range |
| `head_to_head` | Two-team head-to-head record + meetings |
| `team_stats` | A team's W/D/L and goals, with home/away split |
| `standings` | League table for a competition + season, computed from results |
| `search_players` | FIFA players by name / nationality / club / position / min rating |
| `competition_stats` | Goals-per-match, total goals, home/away/draw rates |
| `biggest_wins` | Largest-margin results in a filtered set |
| `list_competitions` | Competitions present in the loaded data |

## Usage

```bash
npm install
npm run build      # compile TypeScript to dist/
npm start          # run the MCP server over stdio
npm test           # run the BDD test suite (vitest)
npm run dev        # run from source without building (tsx)
```

The server speaks MCP over stdio. Point any MCP client at the built binary
(`node dist/index.js`). The data directory defaults to `data/kaggle/` and can be
overridden with the `SOCCER_DATA_DIR` environment variable.

Example client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["dist/index.js"]
    }
  }
}
```

## Testing

BDD (Given/When/Then) scenarios run with [vitest](https://vitest.dev):

- `test/csv.test.ts` — CSV edge cases (quotes, BOM, CRLF).
- `test/normalize.test.ts` — name/date/goal normalization rules.
- `test/matches.test.ts` — match, team and statistical-analysis scenarios.
- `test/players.test.ts` — player and competition (standings) scenarios.
- `test/server.test.ts` — end-to-end MCP tool calls over an in-memory transport.

All scenarios run against the real datasets and assert behaviour (record
consistency, head-to-head symmetry, sorted standings, the known 2019 champion),
not incidental defaults.

## Project layout

```
src/
  csv.ts         CSV parser
  normalize.ts   team/date/goal normalization
  types.ts       Match / Player / TeamRecord domain model
  store.ts       CSV loading + cross-source dedup -> DataStore
  queries.ts     pure query & aggregation functions
  format.ts      human-readable result formatters
  server.ts      MCP tool registration
  index.ts       stdio entrypoint
test/            vitest BDD suites
data/kaggle/     provided CSV datasets
```

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
