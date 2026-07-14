# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes
the provided Brazilian soccer datasets (5 match CSV files + the FIFA player
dataset) as queryable tools for an LLM. Written in C# / .NET 10, tested with
BDD-style scenarios using LightBDD + xUnit.

## What was implemented

### Projects

| Project | Type | Purpose |
|---------|------|---------|
| `src/BrazilianSoccerMcp.Core` | class library | Domain models, CSV loaders, team-name normalization, date parsing, and the `SoccerQueryService` query surface. No I/O / transport concerns. |
| `src/BrazilianSoccerMcp.Server` | console app | MCP server (stdio JSON-RPC transport) exposing the query surface as `[McpServerTool]`s. |
| `tests/BrazilianSoccerMcp.Tests` | xUnit + LightBDD | BDD scenarios covering all required query categories. |

### Data loading

`MatchDataLoader` reads all five match CSVs and normalizes them into a single
`Match` list, mapping each file's idiosyncratic columns onto a common shape
(competition, date, home/away teams + states, scores, season, round/stage, and
the extended BR-Football statistics: corners, attacks, shots, half-time result).
`PlayerDataLoader` reads `fifa_data.csv`, capturing identity/club fields and all
numeric skill ratings (stored in `Player.Attributes`). Rows with unparseable
fields are skipped rather than aborting the whole load.

### Team-name normalization

`TeamNameNormalizer` handles the variations documented in the spec:

* Suffix stripping for `"Palmeiras-SP"`, `"Palmeiras - SP"` and `"América - MG"`.
* Accent-insensitive comparison so `"São Paulo"` matches `"Sao Paulo"`.
* **Disambiguation of same-base clubs**: the canonical identity retains the
  state code, so `Atletico-MG` and `Atletico-PR` stay distinct. Bare-name
  queries (`"Atletico"`) aggregate across states; standings display the bare
  name when only one club with that base name appears in the table, and the
  state suffix when both appear (e.g. `Atletico-MG` vs `Atletico-PR`).

### Date parsing

`DateParser` handles ISO-with-time (`2012-05-19 18:30:00`), ISO date only
(`2023-09-24`) and Brazilian `DD/MM/YYYY` (`29/03/2003`), all in UTF-8.

### Query surface (`SoccerQueryService`)

* **Match queries** — `FindMatchesByTeam`, `FindMatchesBetweenTeams`,
  `FindMostRecentMatch`, `FindDerbies` (Fla-Flu, Majestoso, Grenal, Clássico
  Mineiro, etc.), with competition / season / date-range filters.
* **Team queries** — `GetTeamStats` (wins/draws/losses, goals, home & away
  splits, win rates), `GetHeadToHead`, `BestHomeRecords`, `BestAwayRecords`,
  `TopScoringTeam`.
* **Competition queries** — `GetStandings` (calculated from match results, 3
  pts/win), `AvailableSeasons`. The 2019 Brasileirão standings correctly
  identify Flamengo as champion with 90 points.
* **Player queries** — `FindPlayers` (name/nationality/club/position/overall
  filters), `TopBrazilianPlayers`, `PlayersAtClub`,
  `BrazilianPlayersAtBrazilianClubs`.
* **Statistical analysis** — `AverageGoalsPerMatch`, `WinRateBreakdown`,
  `BiggestWins`.

### MCP tools (`BrazilianSoccerMcp.Server`)

The server hosts 13 tools over stdio via the official
`ModelContextProtocol` 1.4.0 SDK:

`find_matches_by_team`, `find_matches_between_teams`, `find_most_recent_match`,
`find_derbies`, `get_team_stats`, `compare_teams_head_to_head`,
`best_home_records`, `best_away_records`, `top_scoring_team`, `get_standings`,
`available_seasons`, `find_players`, `top_brazilian_players`, `players_at_club`,
`biggest_victories`, `match_averages`.

Each tool returns the spec-aligned, human-readable response format
(e.g. `Flamengo vs Fluminense: ... Head-to-head: Flamengo 12 wins, ...`).

## Build & run

```bash
dotnet build BrazilianSoccerMcp.slnx
dotnet test BrazilianSoccerMcp.slnx        # 22 BDD scenarios

# Run the MCP server (stdio). Data dir defaults to ./data/kaggle.
BSOCCER_DATA=./data/kaggle dotnet run --project src/BrazilianSoccerMcp.Server/BrazilianSoccerMcp.Server.csproj
```

Override the data directory with the `BSOCCER_DATA` environment variable.

## Connecting an MCP client

Add the server to an MCP client config (e.g. Claude Desktop) as a stdio server
pointing at the published `BrazilianSoccerMcp.Server` executable, with
`env.BSOCCER_DATA` set to the repo's `data/kaggle` directory.

## Data sources

See [README data sources section above / `data/kaggle/`] — Kaggle datasets
(CC BY 4.0 / CC0 / Apache 2.0) pre-downloaded into `data/kaggle/`:

* `Brasileirao_Matches.csv` (4,180 matches, 2012-2022)
* `Brazilian_Cup_Matches.csv` (1,337 matches)
* `Libertadores_Matches.csv` (1,255 matches)
* `BR-Football-Dataset.csv` (10,296 matches with extended stats)
* `novo_campeonato_brasileiro.csv` (6,886 matches, 2003-2019)
* `fifa_data.csv` (18,207 players)

## Testing approach

BDD (Given/When/Then) scenarios with LightBDD.XUnit2 — feature files under
`tests/BrazilianSoccerMcp.Tests/`:

* `MatchQueryTests` — find by team / between teams / by season / by competition /
  most-recent / derbies.
* `TeamQueryTests` — stats, head-to-head, same-base disambiguation, home records.
* `PlayerQueryTests` — name search, top Brazilians, club+position, rating filter.
* `CompetitionQueryTests` — calculated standings (incl. the real-world check
  that Flamengo is the 2019 champion with 90 pts), available seasons.
* `StatisticsTests` — average goals, win-rate breakdown summing to 1, biggest
  victories ranking.
* `DataQualityTests` — all six CSVs loadable, team-name variation resolution,
  accent handling, multi-format date parsing.
