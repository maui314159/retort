# Brazilian Soccer MCP

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a queryable knowledge layer over Brazilian soccer datasets — matches,
teams, players, and competitions — so an LLM agent can answer natural-language
questions like *"Who won the 2019 Brasileirão?"*, *"Show me all Fla-Flu
matches"*, or *"Who are the top-rated Brazilian players?"*.

Implemented in TypeScript. Specification: [`TASK.md`](./TASK.md) (and
[`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md)).

## What was built

- **MCP server** (`src/index.ts`) over stdio using the low-level
  `@modelcontextprotocol/sdk` `Server` API with plain JSON-Schema tool
  definitions. Eleven tools cover the five capability categories from the spec:
  match queries, team queries, player queries, competition queries, and
  statistical analysis.
- **Data loader** (`src/loader.ts`) that ingests all six Kaggle CSV files and
  normalizes them into unified `MatchRecord` / `PlayerRecord` shapes (BOM-aware,
  multi-date-format, accent-tolerant).
- **Normalization layer** (`src/normalize.ts`) — team-name flattening (strips
  `-SP` state suffixes, parenthetical notes, accents), Brazilian/ISO date
  parsing, competition aliasing.
- **Query engine** (`src/query.ts`) — pure, deterministic functions for search,
  head-to-head, team statistics, standings (computed from results, 3-1-0),
  average goals, biggest wins, home/away splits, player search, and team
  resolution. Includes a `canonicalMatches` selector that picks one source per
  (competition, season) so overlapping datasets don't double-count fixtures.
- **Formatting** (`src/format.ts`) that mirrors the spec's "Example answer
  format" snippets.
- **BDD test suite** (`tests/bdd.test.ts`) — 29 Given/When/Then scenarios across
  7 features, run with Node's built-in test runner.

## Data sources

Kaggle datasets (pre-downloaded; Kaggle requires an account) live in
`data/kaggle/`:

| File | Records | License |
|------|---------|---------|
| `Brasileirao_Matches.csv` | 4,180 | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | Apache 2.0 |

## Tools exposed

| Tool | Description |
|------|-------------|
| `search_matches` | Matches by team, opponent, competition, season, or date range. |
| `head_to_head` | Two-team comparison with win/draw/loss tally. |
| `team_statistics` | W/D/L, goals, points, win rate; filters by season/competition/venue. |
| `competition_standings` | Standings computed from match results (3 pts/win). |
| `competition_summary` | Available competitions, seasons, and match counts. |
| `average_goals` | Average goals/match and home-win rate. |
| `biggest_wins` | Largest victories by goal difference. |
| `home_away_split` | Home-win / away-win / draw split. |
| `search_players` | FIFA players by name, nationality, club, position, rating. |
| `top_players` | Top-N players by FIFA Overall rating. |
| `resolve_teams` | Disambiguate team names across naming conventions. |

## Getting started

```bash
npm install
npm run build
npm start          # runs the stdio MCP server
```

### Run the tests

```bash
npm test          # builds, then runs the BDD scenarios with node --test
```

### Configure with an MCP client

Add to your client config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/src/index.js"]
    }
  }
}
```

## Example output

```
> competition_standings(Brasileirão, 2019, limit=3)
2019 Brasileirão Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) — GF:86 GA:37 - Champion
2. Palmeiras - 74 pts (21W, 11D, 6L) — GF:61 GA:32
3. Santos - 74 pts (22W, 8D, 8L) — GF:60 GA:33

> top_players(nationality=Brazil, limit=3)
1. Neymar Jr — Overall: 92, Position: LW, Club: Paris Saint-Germain (Brazil)
2. Casemiro — Overall: 88, Position: CDM, Club: Real Madrid (Brazil)
3. Coutinho — Overall: 88, Position: LW, Club: FC Barcelona (Brazil)
```

## Notes on data quality

- **Team-name variation** is handled by stripping state suffixes (`Palmeiras-SP`
  → `palmeiras`), removing parenthetical annotations (`Nacional (URU)`), and
  accent-insensitive tokenization, so the same club matches across files.
- **Date formats** — ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`), and
  Brazilian (`29/03/2003`) — are all parsed to a canonical `YYYY-MM-DD`.
- **UTF-8** is honored throughout (São Paulo, Grêmio, Avaí).
- **Source overlap** between the three Brasileirão/Copa datasets is resolved by
  `canonicalMatches`, which keeps exactly one source per competition+season
  (e.g. historical 2003-2011, `Brasileirao_Matches` 2012-2022, BR-Football Serie
  A 2023+) so standings and tallies are not double-counted.

## License & attribution

This is a demo/non-commercial benchmark. The bundled Kaggle datasets retain
their original licenses (CC BY 4.0, CC0, Apache 2.0) — see the source links in
`README.md` and `TASK.md`. Code in this repository is provided as-is.
