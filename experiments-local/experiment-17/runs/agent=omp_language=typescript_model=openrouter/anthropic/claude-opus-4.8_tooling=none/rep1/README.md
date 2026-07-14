# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a query interface
over Brazilian soccer datasets (matches, teams, competitions, and FIFA players).
An LLM host connects over stdio and answers natural-language questions by
calling the server's tools. Implements the specification in `TASK.md`.

## What it does

Six Kaggle CSVs (~17k deduplicated matches across Brasileirão Série A/B/C, Copa
do Brasil, and Copa Libertadores, plus 18,207 FIFA players) are normalized into
a single in-memory store at startup and served through nine MCP tools.

The hard part is the data, not the protocol: the sources disagree on team names
("Palmeiras-SP" / "Palmeiras", "Atlético Mineiro" / "Atlético-MG"), date formats
(`2023-09-24`, `29/03/2003`, `2012-05-19 18:30:00`), and seasons (the file with
extended stats has no season column and the COVID-delayed 2020 season spilled
into Jan/Feb 2021). `src/normalize.ts` reconciles all of this so that:

- A query in any spelling matches rows loaded from any file.
- Genuinely distinct clubs that share a base name stay separate — `Atlético-MG`
  (Mineiro), `Athletico-PR` (Paranaense), and `Atlético-GO` (Goianiense) are
  three different teams, disambiguated by their state suffix.
- Standings computed from match results reproduce real history: the 2019
  Brasileirão comes out as Flamengo, 90 pts, 38 played — exactly the figure in
  the spec's own example.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range, venue |
| `team_record` | W/D/L and goals for a team, filterable by competition / season / home-away |
| `head_to_head` | Meeting history and win/draw tally between two teams |
| `standings` | League table for a competition + season, computed from results (3pts/win) |
| `search_players` | FIFA players by name / nationality / club / position / min rating |
| `club_roster` | Players at a given club, highest-rated first |
| `league_stats` | Aggregate goals, averages, home/away/draw win rates |
| `biggest_wins` | Largest-margin victories over a filtered set |
| `list_competitions` | Competitions available in the loaded data |

Team and competition arguments are matched flexibly — accents and state
suffixes (`-SP`, ` - RJ`) are ignored, full names map to short keys.

## Usage

```bash
npm install
npm run build
npm start          # runs the MCP server on stdio (reads data/kaggle/)
```

Point an MCP-capable client at the built server:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["dist/server.js"],
      "env": { "SOCCER_DATA_DIR": "data/kaggle" }
    }
  }
}
```

`SOCCER_DATA_DIR` overrides the dataset location (default `data/kaggle`).
For development, `npm run dev` runs the TypeScript source directly via `tsx`.

### Example questions it answers

- "Who won the 2019 Brasileirão?" → `standings` (Flamengo, 90 pts)
- "What is Corinthians' home record in 2022?" → `team_record` (12W 4D 3L)
- "Compare Palmeiras and Santos head-to-head" → `head_to_head`
- "Find the top Brazilian players" → `search_players` (Neymar Jr, 92…)
- "Show the biggest wins in the Brasileirão" → `biggest_wins`
- "What's the average goals per match?" → `league_stats` (~2.57)

## Architecture

```
src/
  normalize.ts  team/date/competition canonicalization (the data-quality core)
  types.ts      Match / Player / standings shapes
  loader.ts     CSV ingestion + cross-source dedupe (one fixture per season)
  store.ts      DataStore: linear-scan query engine over the in-memory corpus
  format.ts     structured results -> readable text answers
  server.ts     MCP server: registers tools over stdio
```

Queries are single linear scans over the in-memory corpus using canonical keys
precomputed at load time — comfortably inside the spec's <2s simple / <5s
aggregate budget.

## Testing

BDD (Given/When/Then) tests with [Vitest](https://vitest.dev):

```bash
npm test           # builds, then runs all suites
```

- `test/normalize.test.ts` — name/date/competition canonicalization, including
  the over-merge / under-merge edge cases.
- `test/store.test.ts` — query behavior against a small, hand-verified fixture
  with exact expected points/records/tallies.
- `test/store.realdata.test.ts` — loads the real CSVs; asserts coverage, the
  one-fixture-per-season dedupe invariant, the 2019 standings, and performance.
- `test/mcp.e2e.test.ts` — spawns the built server over stdio with a real MCP
  client and exercises `listTools` + `callTool`.

## Data limitations

- The FIFA dataset is the 2018/19 edition: most Brazilian stars are at European
  clubs (Neymar at PSG, etc.), and only ~15 Brazilian Série A squads are present,
  so `club_roster` returns results for those clubs (Grêmio, Santos, Internacional,
  Atlético Mineiro, Sport, …) and empty for clubs not in that edition.
- A handful of seasons in the supplementary stats file contain genuine source
  noise (one mislabeled amateur fixture in 2016, fragmented Santa Cruz spellings)
  that leaves a couple of phantom low-game rows in those standings. The core
  standings are computed correctly from the deduplicated match set.

---

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
