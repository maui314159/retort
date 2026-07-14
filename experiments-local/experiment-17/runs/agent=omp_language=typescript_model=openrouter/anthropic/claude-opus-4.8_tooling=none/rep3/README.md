# Brazilian Soccer MCP Server

A TypeScript [Model Context Protocol](https://modelcontextprotocol.io) server
that exposes the Brazilian soccer datasets in `data/kaggle/` as a queryable
knowledge base. An LLM host (e.g. Claude Desktop) can call the tools below to
answer natural-language questions about matches, teams, players, competitions
and statistics. See `TASK.md` / `brazilian-soccer-mcp-guide.md` for the full
specification.

## Quick start

```bash
npm install
npm run build
npm start          # runs the MCP server over stdio
npm test           # runs the BDD (Given/When/Then) test suite
```

The data directory defaults to `<cwd>/data/kaggle` and can be overridden with
the `SOCCER_DATA_DIR` environment variable.

### MCP client configuration

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

## Architecture

All data is loaded into memory once at startup (~16.7k deduplicated matches,
18.2k players) and served by a single in-process query engine, so every lookup
is well within the spec's `<2s` / `<5s` latency budgets.

| File | Responsibility |
|------|----------------|
| `src/csv.ts` | Dependency-free RFC 4180 CSV parser (quotes, embedded commas, BOM, CRLF). |
| `src/normalize.ts` | Team-name normalization and multi-format date parsing. |
| `src/types.ts` | Unified `Match` / `Player` domain model. |
| `src/loader.ts` | Maps each of the 6 CSV schemas into the model and **deduplicates** overlapping sources. |
| `src/queries.ts` | `SoccerKnowledgeBase`: matches, head-to-head, team records, standings, players, statistics. |
| `src/format.ts` | Renders query results into the spec's text answer formats. |
| `src/server.ts` | Registers the MCP tools (transport-agnostic; unit-testable). |
| `src/index.ts` | Executable entry point; connects the server over stdio. |

### Data-quality handling

- **Cross-file duplication.** Brasileirão Série A fixtures appear verbatim in up
  to three files (`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`,
  `BR-Football-Dataset.csv`) and Copa do Brasil in two. Loading them all would
  triple standings and head-to-head totals (the 2019 champion would show 270
  points instead of 90). The loader keeps only the single highest-priority
  source for each `(competition, season)`, so a 20-team season correctly yields
  380 matches.
- **Team-name variations.** Names appear with state suffixes (`Palmeiras-SP`),
  country suffixes (`Nacional (URU)`), or bare (`Palmeiras`). Matching keys are
  accent-folded and lowercased but **retain the suffix as a token**, so
  distinct clubs that share a base name (Atlético-MG vs Athletico-PR) stay
  separate; user queries match across spellings via whole-token containment.
- **Date formats.** ISO (`2023-09-24`), ISO with time (`2012-05-19 18:30:00`)
  and Brazilian (`29/03/2003`) are all unified to ISO `YYYY-MM-DD`.
- **Encoding.** UTF-8 throughout (a leading BOM in `fifa_data.csv` is stripped).
- **FIFA club coverage.** The FIFA 19 dataset only licenses some Brazilian
  clubs (Santos, Grêmio, etc. are present; Flamengo, Palmeiras, Corinthians are
  not). Player-by-club queries reflect the source data.

## MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `league_standings` | "Who won the 2019 Brasileirão?" |
| `search_players` | "Who is Neymar?", "Find all Brazilian players", "Forwards from Brazil" |
| `club_squads` | "Which Brazilian players play for each club?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `dataset_overview` | "What data is available?" |

Each tool returns both a formatted text answer and a `structuredContent`
payload, so callers can consume either representation.

## Testing

Tests are written as BDD Given/When/Then scenarios with [Vitest](https://vitest.dev)
and run against the real datasets:

- `test/csv.test.ts` — parser edge cases (quotes, BOM, CRLF).
- `test/normalize.test.ts` — name keys, fuzzy matching, date parsing.
- `test/queries.test.ts` — query engine over real data (e.g. Flamengo win the
  2019 Série A on 90 pts; cross-file dedup gives 380 matches).
- `test/server.test.ts` — end-to-end MCP client↔server over an in-memory
  transport, including schema validation.

---

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
