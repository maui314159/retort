# Brazilian Soccer MCP

An MCP (Model Context Protocol) server that provides a knowledge-graph
interface for Brazilian soccer data, answering natural-language questions
about players, teams, matches and competitions from the bundled Kaggle
datasets. Implemented in TypeScript on top of
[`@modelcontextprotocol/sdk`](https://github.com/modelcontextprotocol/typescript-sdk).

## What was built

- **Unified dataset** — all 6 CSVs are loaded into canonical match/player
  records. Overlapping fixtures across files are deduplicated in three
  passes: exact (competition, date, teams), fuzzy date clustering (±2 days,
  season-agnostic to bridge calendar-year vs. canonical season labelling),
  and a stale-schedule pass that folds unplayed "NA" placeholder rows into
  the actually-played record of postponed fixtures. 27,654 raw rows become
  ~16,900 verified matches.
- **Team canonicalization** — a registry with a three-layer alias map
  (full spelling, suffix-less base, base+UF pair) plus hand-curated aliases
  unifies cross-dataset variants: "Palmeiras-SP" ≡ "Palmeiras",
  "Vasco-RJ" ≡ "Vasco Da Gama RJ", "Atletico-PR" ≡ "Athletico-PR" ≡
  "Athletico Paranaense", "EC Bahia" ≡ "Bahia-BA", etc. Accents, cedillas
  and multiple date formats (ISO, ISO+time, DD/MM/YYYY) are normalized.
  Result: every Série A season 2003–2022 reproduces the real table exactly
  (correct team counts per era, champions and points).
- **Knowledge graph** — in-memory graph (~36k nodes) of team, player,
  match and competition nodes with HOME_IN / AWAY_IN / WON / LOST / DREW /
  PLAYS_FOR / PLAYED_IN edges; FIFA players at Brazilian clubs are linked
  to their match-data team nodes for cross-file queries.
- **10 MCP tools** (stdio transport):

| Tool | Purpose |
|---|---|
| `dataset_summary` | What is loaded: per-file rows, matches per competition, totals |
| `find_matches` | By team/opponent, competition, season, date range, venue, round/stage |
| `head_to_head` | Two teams: match list + aggregate W/D/L and goals |
| `team_stats` | W/D/L, goals for/against, win rate (season/competition/venue filters) |
| `standings` | League table calculated from results (Série A/B/C, 2003–2023) |
| `search_players` | FIFA players by name/nationality/club/team/position/min rating |
| `brazilian_players_by_club` | Top-rated Brazilians + per-club squad summary |
| `biggest_wins` | Largest victory margins (competition/season filters) |
| `competition_stats` | Avg goals/match, home/draw/away win rates, top-scoring team |
| `graph_neighbors` | Explore the knowledge graph around any entity |

## Usage

```bash
npm install
npm run build      # compile to dist/
npm start          # serve MCP over stdio

npm test           # 67 BDD scenarios (vitest, Given/When/Then structure)
npm run dev        # run from source with tsx
```

Claude Desktop / MCP client configuration:

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

`DATA_DIR` env var overrides the dataset location (default: `data/kaggle`
next to the repository root).

## Testing

BDD scenarios in `test/` mirror the specification's Gherkin features:
normalization, dataset coverage/dedupe, match queries, team statistics,
player queries, competition standings and statistical analysis, plus an
end-to-end MCP protocol suite over an in-memory transport. Standings are
validated against real football history (e.g. Flamengo 90 pts in 2019,
Palmeiras 81 in 2022, Cruzeiro 100 in 2003).

## Data notes

- The extended dataset (`BR-Football-Dataset.csv`) labels matches by
  calendar year, so COVID-delayed 2020-season fixtures carry "2021" — the
  loader reconciles them against the canonical files.
- The same file's 2023 Série A is missing 3 matches (377 rows), so the
  2023 table is slightly incomplete; one row ("Brasilia FC x CA
  Taguatinga", 2016-01-30) is mislabeled as Série A and excluded
  (documented in `src/lib/dataset.ts`).
- The FIFA snapshot (2018-19) lacks some Brazilian clubs (e.g. Flamengo,
  Palmeiras) and some players (e.g. Gabriel Barbosa); tools answer with a
  clear "no players found" message instead of failing.
- `novo_campeonato_brasileiro.csv` records Bahia's state as "BH" instead
  of "BA"; the registry corrects it.

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
