# Brazilian Soccer MCP Server (C#)

A Model Context Protocol (MCP) server that exposes the provided Brazilian soccer datasets as queryable tools. The server is implemented in C# 12 / .NET 10 and answers natural-language-driven questions about matches, teams, players and competitions.

## What was implemented

- **Core library** (`BrazilianSoccerMcp.Core`)
  - Loads and normalizes all six CSV files from `data/kaggle/`:
    - `Brasileirao_Matches.csv`
    - `Brazilian_Cup_Matches.csv`
    - `Libertadores_Matches.csv`
    - `BR-Football-Dataset.csv`
    - `novo_campeonato_brasileiro.csv`
    - `fifa_data.csv`
  - Unified `SoccerMatch` model across heterogeneous match CSVs.
  - Team name normalization that handles state suffixes, full legal names and ASCII/accent variants (e.g. `Palmeiras-SP`, `São Paulo Futebol Clube`, `Sao Paulo`).
  - Multi-format date parsing (ISO, Brazilian, with/without time).
  - Query service supporting match lookup, head-to-head, team/venue statistics, player search, league tables, biggest wins and aggregate competition statistics.

- **MCP server** (`BrazilianSoccerMcp.Server`)
  - `stdio` transport for Model Context Protocol clients.
  - Tools:
    - `SearchMatches`
    - `GetHeadToHead`
    - `GetTeamStatistics`
    - `GetHomeAwayStatistics`
    - `SearchPlayers`
    - `GetStandings`
    - `GetBiggestWins`
    - `GetCompetitionStatistics`
    - `GetBestAwayRecords`
  - Logging is redirected to `stderr` so that `stdout` stays a clean MCP JSON-RPC stream.

- **Tests** (`BrazilianSoccerMcp.Tests`)
  - BDD-style xUnit tests covering data loading, normalization, match/team/player/competition queries, statistics and query performance.
  - 38 tests, all passing.

## Build

```bash
dotnet build
```

## Run tests

```bash
dotnet test
```

## Run the server

```bash
dotnet run --project BrazilianSoccerMcp.Server -- data/kaggle
```

## Data sources

See `brazilian-soccer-mcp-guide.md` and `TASK.md` for the full specification and dataset attributions.
