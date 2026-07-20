# Interfaces

## HTTP routes

(none) — the server speaks MCP over stdio, not HTTP.

## MCP tools

Registered in `src/server.ts:createServer` (10 tools, all returning text content):

| Tool | Inputs | Description |
|------|--------|-------------|
| `dataset_summary` | (none) | Row counts per source file, matches per competition, teams, players, season coverage, graph node count |
| `find_matches` | `team?`, `opponent?`, `competition?`, `season?`, `dateFrom?`, `dateTo?`, `venue? (home/away/any)`, `round?`, `limit? (1-100)` | Find matches by team/opponent/competition/season/date range/venue/round; accents and state suffixes accepted |
| `head_to_head` | `teamA`, `teamB`, `competition?`, `season?`, `limit? (1-50)` | All matches between two teams plus aggregate W/D/L and goals |
| `team_stats` | `team`, `season?`, `competition?`, `venue?` | Win/draw/loss record, goals for/against, win rate |
| `standings` | `season`, `competition?` | Points table computed from results (3/1/0; tiebreakers wins, GD, GF); Série A/B/C only |
| `search_players` | `name?`, `nationality?`, `club?`, `team?`, `position?`, `minOverall?`, `limit? (1-100)` | Search FIFA player database, sorted by overall rating; position groups supported |
| `brazilian_players_by_club` | `top? (1-50)` | Count and average rating of Brazilian players per Brazilian club, plus top-rated Brazilians |
| `biggest_wins` | `competition?`, `season?`, `limit? (1-50)` | Largest victory margins, optionally filtered |
| `competition_stats` | `competition?`, `season?` | Average goals/match, home/draw/away win rates, highest-scoring team |
| `graph_neighbors` | `entity`, `edgeType?`, `limit? (1-100)` | Explore knowledge-graph relationships around a team, player or competition |

Team/competition resolution errors return `isError: true` text results.

## CLI commands

(none) — single entry point `src/index.ts` (`npm start` / `node dist/index.js`), configurable via `DATA_DIR` env var.

## Library API

Key exports usable without the MCP layer:

- `src/lib/dataset.ts`: `loadDataset(dataDir?) → Dataset` (`matches`, `players`, `teams: TeamRegistry`, `loadReport`)
- `src/lib/queries.ts`: `findMatches`, `headToHead`, `teamRecord`, `computeStandings`, `searchPlayers`, `brazilianPlayersByClub`, `competitionStats`, `biggestWins`, `resolveCompetition`, `resolveTeamOrError`
- `src/lib/graph.ts`: `KnowledgeGraph.fromDataset(dataset)`, `.neighbors(nodeId, edgeType?)`, static node-id builders
- `src/lib/teams.ts`: `TeamRegistry.resolve(query) → TeamResolution`
- `src/lib/text.ts` / `src/lib/dates.ts`: `normalizeText`, `splitTeamSuffix`, `parseDateTime`, `parseYear`
- `src/lib/format.ts`: eight `format*` renderers matching the spec's answer styles

## Data schemas

Domain records (`src/lib/types.ts`):

- `Competition` enum: Brasileirão Série A, Série B, Série C, Copa do Brasil, Copa Libertadores
- `Team`: key, name, uf (state)
- `Match`: id, date/time, competition, season, round/stage, home/away team keys, goals, optional `MatchStats` (corners, attacks, shots, half-time results)
- `Player` (FIFA data): id, name, age, nationality, overall, potential, club, position, jersey number, height/weight

Knowledge graph (`src/lib/graph.ts`): node types `team | player | match | competition`; edge types `HOME_IN`, `AWAY_IN`, `WON`, `LOST`, `DREW`, `PLAYS_FOR`, `HAS_NATIONALITY`, `PLAYED_IN`.

Source data: six Kaggle CSVs under `data/kaggle/` (Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data), deduplicated across overlapping files at load time.
