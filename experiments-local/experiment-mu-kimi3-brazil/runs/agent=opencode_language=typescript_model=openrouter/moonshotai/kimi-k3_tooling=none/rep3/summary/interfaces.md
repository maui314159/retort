# Interfaces

## HTTP routes

(none) — the server speaks MCP over stdio, not HTTP.

## MCP tools (registered in `src/server.ts:createServer`)

| Tool | Inputs (zod) | Returns |
|------|--------------|---------|
| `dataset_overview` | — | Row counts per source CSV, unique match/team/player counts, competitions, season coverage |
| `find_matches` | team?, opponent?, competition?, season?, from?, to?, venue? (home/away/any), round?, stage?, limit? | `{count, matches[]}` |
| `head_to_head` | teamA, teamB, competition? | W/D/L + goals summary and match list |
| `team_record` | team, season?, competition?, venue? | `TeamRecord` (matches, W/D/L, GF/GA, winRate) |
| `team_competitions` | team | Competitions with seasons + match counts |
| `league_standings` | season, competition? (default Brasileirão Série A) | `StandingRow[]` (rank, points, champion/relegation notes); MCP error if no played matches |
| `cup_finals` | season? | Copa do Brasil final-round matches per season |
| `search_players` | name?, nationality?, club?, position?, minOverall?, brazilianClubsOnly?, limit? | `{count, players[]}` |
| `top_players` | nationality?, club?, position?, brazilianClubsOnly?, limit? (default 10) | Highest-rated players |
| `players_by_club_summary` | nationality, brazilianClubsOnly? | Count + avg rating grouped by club |
| `competition_stats` | competition?, season? | Matches played, total/avg goals, home/draw/away win rates |
| `biggest_wins` | competition?, season?, limit? | Largest victory margins |
| `best_home_records` | competition?, season?, limit?, minMatches? | Teams ranked by home win rate |
| `best_away_records` | competition?, season?, limit?, minMatches? | Teams ranked by away win rate |
| `top_scoring_teams` | season?, competition?, limit? | Teams by goals scored |

All tools return JSON pretty-printed inside a single `text` content block; `league_standings` is the only one that emits `isError`.

## MCP resources

| URI | Description |
|-----|-------------|
| `soccer://overview` | Summary of the loaded datasets (same payload as `dataset_overview`) |

## CLI commands

Single stdio server: `node dist/index.js` (bin `brazilian-soccer-mcp`); dev via `tsx src/index.ts`. Env var `SOCCER_DATA_DIR` overrides data-directory discovery.

## Library API (used by tests)

- `context.ts`: `getContext(dataDir?) -> AppContext {dataset, built, queries}` (cached singleton when no dir given)
- `queries.ts`: `SoccerQueries` methods — `findMatches`, `headToHead`, `teamRecord`, `teamCompetitions`, `searchPlayers`, `playersByClubSummary`, `standings`, `cupFinals`, `competitionSeasons`, `competitionStats`, `biggestWins`, `bestHomeRecords`, `bestAwayRecords`, `topScoringTeams`, `overview`
- `graph.ts`: `KnowledgeGraph` (addNode/addEdge/neighbors/nodeCount), `buildGraph(matches, players)`
- `loader.ts`: `loadDataset(dir?)`, `findDataDir()`
- `normalize.ts`: name/date/competition normalization functions (see modules.md)

## Data schema

In-memory only (no DB). Key shapes from `src/types.ts`:

- `Match`: id (`date|homeKey|awayKey`), date (ISO), season, competition (one of 5 canonical labels), round, stage, homeTeam/awayTeam (`TeamRef {key, name, raw}`), homeGoals/awayGoals (nullable), arena, sources[], stats? (corners/shots/attacks)
- `Player`: id, name, age, nationality, overall, potential, club, clubKey, position, jerseyNumber, height, weight
- Graph nodes: team, player, competition, season, match, country; edges: PLAYED_HOME, PLAYED_AWAY, IN_COMPETITION, IN_SEASON, PLAYS_FOR, HAS_NATIONALITY
- Sources: six CSVs under `data/kaggle/` (Brasileirão, Copa do Brasil, Libertadores, historical, extended-stats, FIFA players)
