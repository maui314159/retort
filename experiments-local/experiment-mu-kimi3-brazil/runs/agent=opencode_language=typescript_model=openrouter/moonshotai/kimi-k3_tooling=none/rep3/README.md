# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in **TypeScript**, that provides a
knowledge-graph interface over Brazilian soccer data. It answers natural-language
questions about matches, teams, players and competitions using the six Kaggle
datasets in `data/kaggle/`.

Specification: see [`TASK.md`](TASK.md) / `brazilian-soccer-mcp-guide.md`.

## What was built

```
src/
  types.ts      Domain types (Match, Player, TeamRecord, StandingRow, ...)
  normalize.ts  Team-name / date / competition normalization + aliases
  loader.ts     CSV loading, cross-source deduplication, season repair
  graph.ts      In-memory knowledge graph (nodes + edges + query indexes)
  queries.ts    Query engine: the five question categories from the spec
  context.ts    Shared wiring (dataset -> graph -> queries)
  server.ts     MCP server: 15 tools + 1 resource
  index.ts      stdio entry point
tests/          Vitest BDD (Given/When/Then) suite, 75 tests
```

### Knowledge graph

Nodes: **Team, Player, Competition, Season, Match, Country**.
Edges: `PLAYED_HOME`, `PLAYED_AWAY`, `IN_COMPETITION`, `IN_SEASON`,
`PLAYS_FOR` (player -> team), `HAS_NATIONALITY` (player -> country).
Indexes over the graph (matches-by-team, players-by-club, ...) keep simple
lookups at O(team matches) and aggregates at O(dataset) with a single pass.

### Data unification highlights

- **Team name normalization** — every naming variant in the sources
  ("Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Sport Club Corinthians
  Paulista", "América FC (Minas Gerais)", "Guaraní (PAR)") maps to a canonical
  key via suffix parsing, accent stripping and an alias table. Same-name
  clubs from different states stay distinct (Botafogo-RJ vs Botafogo-PB);
  renamed clubs merge (Atlético-PR/Athletico Paranaense, Bragantino/Red Bull
  Bragantino).
- **Date formats** — ISO (`2023-09-24`), ISO datetime (`2012-05-19 18:30:00`)
  and Brazilian `DD/MM/YYYY` all normalize to ISO dates.
- **Cross-source deduplication** — matches are keyed by `(date, home, away)`;
  a second pass merges fixtures whose dates drift by <= 2 days across sources
  (e.g. 22:00 kick-offs logged on the next day); unplayed placeholder rows
  (goals = `NA`/`-`) are dropped when a played record exists.
- **Season repair** — the COVID-delayed 2020 Brasileirão (played Aug 2020 –
  Feb 2021) is fully assigned to season 2020 even for matches played in
  early 2021.
- Result: every Brasileirão Série A season 2003-2022 has the exact real-world
  match count (552/462/380), and calculated standings reproduce history
  (e.g. 2019: Flamengo champion with 90 pts; 2003: Cruzeiro with 100 pts;
  2020: Flamengo with 71 pts). The 2023 season has 377 of 380 matches —
  three late fixtures are genuinely absent from the source export.
- One known source anomaly is filtered: a friendly ("Brasilia FC 1-1 CA
  Taguatinga", 2016-01-30) mislabeled as "Serie A" in BR-Football-Dataset.

## Usage

```bash
npm install
npm run build     # compiles to dist/
npm start         # runs the MCP server over stdio
npm test          # runs the BDD test suite (vitest)
```

Register with an MCP client (e.g. Claude Desktop / opencode):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/path/to/this/repo/dist/index.js"]
    }
  }
}
```

Data directory resolution: `SOCCER_DATA_DIR` env var, else `./data/kaggle`,
else walking up from the module directory.

## MCP tools (15)

| Tool | Answers |
|------|---------|
| `dataset_overview` | Row counts per CSV, unique matches, teams, players, coverage |
| `find_matches` | Matches by team/opponent/competition/season/date range/venue/round/stage |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches" + W/D/L summary |
| `team_record` | "Corinthians' home record in 2022" (W/D/L, GF/GA, win rate) |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `league_standings` | "Who won the 2019 Brasileirão?" (calculated table, champion + relegation) |
| `cup_finals` | "Find all Copa do Brasil finals" |
| `search_players` | "Who is Gabriel Barbosa?" name/nationality/club/position search |
| `top_players` | "Who are the highest-rated Brazilian players?" |
| `players_by_club_summary` | "Brazilian players at Brazilian clubs" (count + avg rating) |
| `competition_stats` | "Average goals per match", home/draw/away win rates |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `best_home_records` | "Which team has the best home record?" |
| `best_away_records` | "Which team has the best away record?" |
| `top_scoring_teams` | "Which team scored the most goals in Série A 2023?" |

Plus one resource: `soccer://overview` (dataset summary as JSON).

## Testing

`npm test` — 75 Vitest tests in BDD Given/When/Then style covering:

- **Match queries** — Fla-Flu derby, Palmeiras 2023, cup finals,
  Libertadores stages, venue filters, date ranges
- **Team queries** — Corinthians 2022 home record (19 matches), top scorers
  2023, best home records, competition lists
- **Player queries** — Brazilians (Neymar Jr 92 leads), club squads,
  forwards/goalkeepers by group, per-club summaries
- **Competition queries** — 2019/2003/2020 standings vs historical fact,
  relegation zones, 2018 Libertadores bracket, Série B
- **Statistics** — goal averages, home advantage, biggest wins, head-to-head
  consistency, cross-file (player + match) queries, dedup invariants
- **MCP protocol** — end-to-end over `InMemoryTransport`: tool listing,
  tool calls, error paths, resource read
- **Performance** — lookups ~ms, aggregates well under spec limits

## Data sources (pre-downloaded in `data/kaggle/`)

| File | Rows | License |
|------|------|---------|
| `Brasileirao_Matches.csv` | 4,180 | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | Apache 2.0 |

After cross-source deduplication: **16,778 unique matches** and
**18,207 players** across **479 teams**.
