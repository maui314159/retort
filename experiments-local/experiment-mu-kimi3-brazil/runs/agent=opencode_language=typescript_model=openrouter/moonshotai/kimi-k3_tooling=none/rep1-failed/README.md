# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph-style
query interface over Brazilian soccer data: matches, teams, players and
competitions. Built in TypeScript on top of the official
`@modelcontextprotocol/sdk`.

Implements the specification in [`TASK.md`](TASK.md) (same content as
`brazilian-soccer-mcp-guide.md`).

## What it does

- Loads all 6 provided Kaggle CSVs into a unified, in-memory knowledge store.
- Normalizes team names across files (state suffixes, legal forms, accents,
  historical renames like Atlético-PR → Athletico-PR) via a canonical club
  registry.
- Handles all three date formats (ISO, ISO datetime, DD/MM/YYYY) and UTF-8
  Brazilian Portuguese text.
- **Deduplicates matches across files** — the same real-world fixture appears
  in up to three sources with dates that disagree by a day or two, so identity
  is `(competition, season, home, away, score)`. This makes computed league
  tables exact (e.g. the 2019 Brasileirão comes out at 380 matches and the
  historically correct final standings).
- Serves 16 MCP tools over stdio covering the five required capability
  categories: match queries, team queries, player queries, competition
  queries and statistical analysis.

## Usage

```bash
npm install
npm run build
npm start          # serves MCP over stdio
```

Dev mode without building:

```bash
npm run dev        # tsx src/index.ts
```

Point your MCP client at the server, e.g. Claude Desktop config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/path/to/repo/dist/index.js"]
    }
  }
}
```

Set `DATA_DIR` to override the default `data/kaggle` location.

### Smoke test (spawns the real server over stdio)

```bash
node scripts/e2e-smoke.mjs
```

## MCP tools

| Category | Tool | Purpose |
|---|---|---|
| Matches | `search_matches` | By team, opponent, competition, season, date range, stage |
| Matches | `head_to_head` | All-time record between two teams + recent meetings |
| Matches | `last_meeting` | Most recent match between two teams |
| Teams | `team_statistics` | W/D/L, goals, home/away splits, per-competition breakdown |
| Teams | `team_competitions` | Competitions a team played in, with match counts |
| Teams | `top_scoring_teams` | Goal ranking per competition/season |
| Players | `search_players` | Name/nationality/club/position filters, sorted by rating |
| Players | `player_details` | Full profile of the best name match |
| Players | `players_per_club` | Players per club for a nationality, with avg rating |
| Competitions | `competition_standings` | League table computed from results (CBF tie-breaks) |
| Competitions | `competition_finals` | Copa do Brasil / Libertadores finals |
| Competitions | `competition_seasons` | Season coverage per competition |
| Stats | `competition_stats` | Goals-per-match, home/draw/away win rates |
| Stats | `biggest_wins` | Largest-margin victories |
| Stats | `best_venue_records` | Best home or away records by win rate |
| Meta | `dataset_summary` | Loaded files, totals, coverage |

## Testing

BDD-style tests (Given/When/Then) with vitest, covering the spec's Gherkin
scenarios plus 24 of the spec's sample questions executed end-to-end through
an in-memory MCP client:

```bash
npm test
```

- `tests/normalization.test.ts` — team-name variants, date formats, UTF-8
- `tests/matches.test.ts` — match queries (teams, season, dates, stages)
- `tests/teams.test.ts` — team statistics and rankings
- `tests/players.test.ts` — player search and filters
- `tests/competitions.test.ts` — standings (2019 checked against history),
  finals, seasons
- `tests/stats.test.ts` — aggregates, biggest wins, venue records
- `tests/coverage.test.ts` — all 6 files loadable, dedupe correctness
- `tests/server.test.ts` — MCP protocol end-to-end (tool list, calls, errors)
- `tests/questions.test.ts` — 24 spec sample questions via the protocol

Performance (well within the spec's <2s lookups / <5s aggregates): full data
load ≈ 1s at startup; thereafter lookups ≈ 5ms, aggregates ≈ 15–30ms.

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

### Data notes

- `Brasileirao_Matches.csv`: 82 rows carry `NA` goals (unplayed fixtures) and
  are skipped.
- The FIFA edition included here lists no Flamengo/São Paulo squads and no
  Gabriel Barbosa; the tools answer such lookups gracefully with an empty
  result instead of an error.
- Match dates can differ by a day or two between source files for the same
  fixture; the dedupe identity therefore ignores the exact date (see above).
