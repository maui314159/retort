# Interfaces

## HTTP routes

(none) — the server speaks MCP over stdio (`WithStdioServerTransport()`), not HTTP.

## CLI commands

(none) — `Program.cs` passes `args` to `Host.CreateApplicationBuilder` but declares
no subcommands or flags. The executable's only mode is "run as an MCP stdio server".

## MCP tools

All ten tools are discovered by `WithToolsFromAssembly()` from the two
`[McpServerToolType]` classes. Every tool returns a preformatted, human-readable
`string` (no structured JSON payloads).

| Tool | Parameters | Returns | Declared in |
|------|-----------|---------|-------------|
| `FindMatches` | `team?`, `opponent?`, `competition?`, `season?`, `fromDate?`, `toDate?`, `limit=20` | Header line + `- {match summary}` lines | `Tools/MatchTools.cs` |
| `GetTeamStats` | `team`, `competition?`, `season?`, `homeOnly=false`, `awayOnly=false` | `TeamStats.Format()` block (matches, W/D/L, GF/GA, points, win rate) | `Tools/MatchTools.cs` |
| `CompareTeams` | `teamA`, `teamB` | Head-to-head tally + up to 20 match lines, with an `... (n more matches in dataset)` tail | `Tools/MatchTools.cs` |
| `SearchPlayers` | `name?`, `nationality?`, `club?`, `position?`, `minOverall?`, `limit=10` | Numbered player list sorted by overall desc | `Tools/SoccerTools.cs` |
| `GetClubPlayers` | `club`, `limit=20` | Numbered player list + average rating | `Tools/SoccerTools.cs` |
| `GetStandings` | `competition`, `season` | Up to 20 ranked rows: `{pos}. {team} - {pts} pts ({W}W, {D}D, {L}L)` | `Tools/SoccerTools.cs` |
| `GetChampion` | `competition`, `season` | Single line for the top-ranked team | `Tools/SoccerTools.cs` |
| `GetAggregateStats` | `competition?`, `season?` | Avg goals/match, home/away/draw rates, total goals | `Tools/SoccerTools.cs` |
| `GetBiggestVictories` | `competition?`, `limit=10` | Numbered match list with goal margin | `Tools/SoccerTools.cs` |
| `ListTeams` | `filter?`, `limit=50` | Comma-joined team display names | `Tools/SoccerTools.cs` |

## Library API

`SoccerDataService` is public and independently constructible with an explicit
`dataDirectory` (`new SoccerDataService(path)`), which is how the tests drive it.
Query surface: `EnsureLoaded()`, `Matches`, `Players`, `MatchesForTeam(team)`,
`HeadToHead(a, b)`, `StatsForTeam(team, competition?, season?, homeOnly, awayOnly)`,
`Standings(competition, season)`, `BiggestVictories(top, competition?)`,
`AllTeams()`, `DisplayName(key)`, `ResolveTeamKey(team)`, plus the static
`ParseInt(string?)` / `ParseDate(string?)` helpers.

`TeamNameNormalizer.StripSuffix(raw)` and `TeamNameNormalizer.CanonicalKey(raw)`
are public statics; `DataPathResolver.ResolveDataDirectory()` likewise.

## Data schema

No database. Two in-memory `List<T>` collections, populated once from CSV.

**`Match`** (unified across the five match CSVs): `Competition`, `Source`,
`HomeTeam`, `AwayTeam`, `HomeTeamKey`, `AwayTeamKey`, `HomeGoals?`, `AwayGoals?`,
`Date?`, `Season?`, `Round?`, `Stage?`, `Arena?`, `HomeState?`, `AwayState?`, and
the BR-Football-Dataset-only extras `HomeCorners?`/`AwayCorners?`,
`HomeShots?`/`AwayShots?`, `HomeAttacks?`/`AwayAttacks?`. Computed: `HomeWin`,
`AwayWin`, `Draw`, `TotalGoals?`, `GoalDifference?` (absolute), `Summary`.

**`Player`** (from `fifa_data.csv`): `Id?`, `Name`, `Age?`, `Nationality`,
`Overall?`, `Potential?`, `Club`, `Position?`, `JerseyNumber?`, `PreferredFoot?`,
`Height?`, `Weight?`, `Value?`, `Wage?`, `Summary`.

**`TeamStats`** (computed): `Team`, `Matches`, `Wins`, `Draws`, `Losses`,
`GoalsFor`, `GoalsAgainst`; derived `Points` (3/1/0), `WinRate`, `GoalsPerMatch`.

**`StandingsEntry`** (computed): `Position`, `Team`, `Played`, `Wins`, `Draws`,
`Losses`, `GoalsFor`, `GoalsAgainst`, `GoalDifference`, `Points`, `Champion`.

**Competition labels** assigned at load time: `Brasileirão`, `Copa do Brasil`,
`Copa Libertadores`, `Brasileirão Série A/B/C` (mapped from the `tournament`
column of BR-Football-Dataset), and `Brasileirão (Histórico)`. A dictionary
`_teamKeyToDisplay` maps canonical key → display name, populated during load.
