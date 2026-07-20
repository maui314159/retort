# Interfaces

## HTTP routes

(none — stdio transport only)

## MCP protocol methods (JSON-RPC 2.0, line-delimited stdio)

Handled in `Mcp/McpServer.cs:HandleMessage`: `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list` (empty), `prompts/list` (empty), `notifications/*` (ignored). Unknown methods return `-32601`. Server name `brazilian-soccer-mcp` v1.0.0, protocol `2024-11-05`.

## MCP tools (13, registered in `Tools/ToolRegistry.cs`)

| Tool | Description |
|------|-------------|
| `find_matches` | Find matches by team/opponent/competition/season/date range/venue/round |
| `head_to_head` | All matches between two teams plus win/draw tally |
| `team_statistics` | Win/draw/loss record with season/competition/venue filters |
| `competition_standings` | League table (3/1/0 points) for a season |
| `competition_stats` | Averages and outcome rates for a competition/season slice |
| `biggest_wins` | Largest victory margins |
| `search_players` | Player search by name/nationality/club/position |
| `club_players` | Players at a club (cross-file team-key join) |
| `top_players` | Highest-rated players, optional nationality/position filter |
| `brazilian_players_summary` | Per-club summary of Brazilian players at Brazilian clubs |
| `list_competitions` | Competitions in the dataset |
| `list_teams` | Teams in the dataset |
| `graph_stats` | Node/edge counts of the knowledge graph |

All tools return human-readable text content (not structured JSON).

## CLI

Single executable: `BrazilianSoccerMcp [data-dir]`; data dir also resolvable via `BRAZILIAN_SOCCER_DATA_DIR` or upward search for `data/kaggle` (`Program.cs:ResolveDataDir`). Exits 1 if not found.

## Data schema (in-memory, from data/kaggle CSVs)

- `Match` record: Competition, Season, Round (text), Date, HomeTeam/AwayTeam (raw), HomeKey/AwayKey (normalized), HomeGoals/AwayGoals (nullable — "NA" = not played), Source file.
- `Player` record (FIFA dataset): name, nationality, club + normalized ClubKey, position, overall rating; helpers `IsGoalkeeper`, attacking-position flag.
- `KnowledgeGraph`: TeamNode (with alias resolution via `TeamNameNormalizer`), player/competition/season/match nodes; `Stats()` reports node/edge counts.
