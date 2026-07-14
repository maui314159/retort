# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge-graph
interface over Brazilian soccer datasets (matches, teams, players, competitions).
Connect it to an MCP-capable LLM host (e.g. Claude Desktop) to answer natural
language questions about Brazilian football.

Specification: `brazilian-soccer-mcp-guide.md`.

## What it does

Six Kaggle CSV files in `data/kaggle/` are loaded once at startup into an
in-memory graph of ~16.6k de-duplicated matches and 18.2k FIFA players, then
served over stdio as MCP tools.

The datasets overlap (Brasileirão Série A 2012–2019 appears in three files with
divergent team spellings), so loading selects a single **canonical source per
`(competition, season)`** by priority rather than fuzzy row de-duplication —
this guarantees every real game is counted exactly once, which standings and
win-rate math depend on. Extended statistics (corners/shots/attacks) from
`BR-Football-Dataset.csv` are merged into the canonical matches where available.

### Tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team / opponent / home / away / competition / season / date range. Adds a head-to-head summary when `team` + `opponent` are both given. |
| `team_record` | W/D/L, goals for/against, and win rate for a team; scopable by competition, season, and venue (home/away). |
| `head_to_head` | Aggregated rivalry record between two teams plus recent matches. |
| `find_players` | FIFA players by name / nationality / club / position / min rating, ranked by overall. |
| `standings` | League table for a competition + season, computed from results (3 pts win / 1 draw), tie-broken by goal difference. |
| `competition_stats` | Match count, total goals, goals/match, home/away win counts, home win rate. |
| `biggest_wins` | Largest goal-margin victories, optionally scoped by competition/season. |

Team names are normalized, so `Flamengo`, `Flamengo-RJ`, and `flamengo` all
match, while `Atlético-MG` and `Atlético-GO` stay distinct. Dates are parsed
from ISO (`2023-09-24`), ISO-with-time (`2012-05-19 18:30:00`), and Brazilian
(`29/03/2003`) formats. UTF-8 (accents, cedilla) is handled throughout.

### Competitions covered

Brasileirão Série A (2003–2023), Série B & C, Copa do Brasil, and Copa
Libertadores.

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start          # serve over stdio (production: dist/index.js)
npm run dev        # serve over stdio from TypeScript source (tsx)
```

Set `BRAZILIAN_SOCCER_DATA_DIR` to point at an alternate data directory;
otherwise the bundled `data/kaggle` is used. Startup logs go to stderr to keep
the stdout JSON-RPC stream clean.

### Claude Desktop config

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

## Example questions

- "Who won the 2019 Brasileirão?" → `standings` (Flamengo, 90 pts, champion)
- "Show me all Flamengo vs Fluminense matches" → `find_matches` + head-to-head
- "Find the top Brazilian players" → `find_players` (Neymar Jr, 92)
- "What's the average goals per match in the 2019 Brasileirão?" → `competition_stats`
- "Compare Palmeiras and Santos head-to-head" → `head_to_head`
- "What are the biggest wins in the data?" → `biggest_wins`

## Tests

BDD (Given/When/Then) scenarios with [Vitest](https://vitest.dev):

```bash
npm test
```

Coverage spans the normalization rules, the CSV reader quirks, the query layer
against the real bundled data (anchored on the fully-present 2019 Série A
season), and an end-to-end MCP client↔server round-trip over an in-memory
transport.

## Project layout

```
src/
  normalize.ts  team-name + date normalization
  csv.ts        zero-dependency CSV reader
  models.ts     unified Match / Player domain types
  loader.ts     CSV → models, canonical-source selection, stats merge
  service.ts    SoccerGraph query layer (matches/teams/players/standings/stats)
  format.ts     spec-shaped human-readable formatting
  server.ts     MCP server + tool definitions
  index.ts      stdio entrypoint
test/           BDD test suites
```

## Data limitations

The provided FIFA snapshot does not include every current Brazilian player
(e.g. Gabriel Barbosa is absent) and lists many players at their European
clubs. The 2022 Brasileirão match data is partial (season truncated). Queries
report results strictly from the bundled data.

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
