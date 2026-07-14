# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes the bundled Brazilian
soccer Kaggle datasets as a queryable knowledge graph for any MCP-compatible
LLM client (Claude Desktop, etc.). It answers natural-language questions about
matches, teams, players, and competitions across all six provided CSVs.

## What it does

Loads six Kaggle datasets into an in-memory, normalized model and exposes
eight MCP tools covering the five required query categories from
`TASK.md`:

| Tool | Category | Purpose |
|------|----------|---------|
| `search_matches` | Match queries | Find matches by team, opponent, competition, season, date range |
| `team_statistics` | Team queries | Win/loss/draw record, goals, points; filter by venue/competition/season |
| `compare_teams` | Team queries | Head-to-head summary + both teams' overall records |
| `search_players` | Player queries | FIFA player search by name/nationality/club/position/rating |
| `competition_standings` | Competition queries | Computed standings (3 pts/win), champion, relegation zone |
| `match_statistics` | Statistical analysis | Avg goals, home/away win rates, biggest victories |
| `list_teams` | Catalog | Enumerate/resolve team-name variants |
| `list_competitions` | Catalog | Competitions + seasons present in the data |

## Data sources (in `data/kaggle/`)

- `Brasileirao_Matches.csv` — Brasileirão Série A (CC BY 4.0)
- `Brazilian_Cup_Matches.csv` — Copa do Brasil (CC BY 4.0)
- `Libertadores_Matches.csv` — Copa Libertadores (CC BY 4.0)
- `BR-Football-Dataset.csv` — extended match stats (CC0)
- `novo_campeonato_brasileiro.csv` — historical Brasileirão 2003–2019 (CC BY 4.0)
- `fifa_data.csv` — FIFA player database (Apache 2.0)

## Data-quality handling

- **Team-name normalization**: a curated alias map reconciles variants across
  sources — `Palmeiras-SP`, `Palmeiras SP`, and `Palmeiras` all resolve to one
  node; `Atletico-MG` and `Atletico-PR` stay distinct (Atlético Mineiro vs
  Athletico Paranaense); accented (`São Paulo`) and unaccented (`Sao Paulo`)
  forms merge.
- **Date parsing**: ISO-with-time (`2012-05-19 18:30:00`), ISO-date
  (`2023-09-24`), and Brazilian (`29/03/2003`) formats all parse to a UTC day.
- **Cross-file deduplication**: the same physical match appears in multiple
  sources (e.g. Brasileirao_Matches + BR-Football + novo for 2012–2019).
  Duplicate records are merged on (season, competition, teams, score), keeping
  the first-seen record and enriching it with extended stats (corners/shots/
  attacks/arena) from the duplicate. Without this, standings and team records
  would double-count — e.g. Flamengo's 2019 Brasileirão correctly computes to
  38 matches / 90 points (champion), matching the historical record.

## Build & run

```bash
npm install
npm run build          # TypeScript -> dist/
npm start              # run the compiled server over stdio
# or for development:
npm run dev            # run via bun without compiling
```

Override the data directory with `BRAZILIAN_SOCCER_DATA_DIR=/path/to/csvs npm start`.

### Connecting from Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/brazilian-soccer-mcp/dist/index.js"]
    }
  }
}
```

## Example queries

- "Who won the 2019 Brasileirão?" → `competition_standings` → Flamengo, 90 pts.
- "Show me all Flamengo vs Fluminense matches" → `search_matches` (Fla-Flu derby across Brasileirão + Copa do Brasil).
- "What is Corinthians' home record in 2022?" → `team_statistics` (venue=home).
- "Who are the top Brazilian players?" → `search_players` (nationality=Brazil, sorted by overall).
- "What's the average goals per match in the 2023 Brasileirão?" → `match_statistics`.

## Testing

BDD (Given/When/Then) test suite with vitest, exercising every tool against the
real datasets:

```bash
npm test
```

The suite validates match/team/player/competition/statistical queries plus
data-quality invariants (normalization, date parsing, deduplication, and a
server-registration smoke test).

## Project layout

```
src/
  index.ts              # MCP server entry (stdio transport)
  tools.ts              # tool handlers + MCP registration
  data/
    types.ts            # domain types (MatchRecord, Player, ...)
    loader.ts           # CSV loading + dedup + indexing + standings
    normalize.ts        # curated team-name alias map + TeamRegistry
    dates.ts            # multi-format date parsing
    query.ts            # pure query functions + formatters
tests/
  bdd.test.ts           # GWT-style BDD suite
```
