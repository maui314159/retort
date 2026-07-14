# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that exposes the bundled Kaggle
Brazilian soccer datasets (Brasileirão, Copa do Brasil, Libertadores,
historical 2003-2019 matches, extended match statistics, and the FIFA
player database) to an LLM host as queryable tools.

The server is implemented in **C# / .NET 10** and speaks the standard
MCP JSON-RPC 2.0 protocol over stdio, so any MCP-compatible client (Claude
Desktop, an IDE plugin, a custom agent loop) can launch it directly.

## Specification

See [`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md) and
[`TASK.md`](./TASK.md) for the full requirements.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely
available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`

## Project Layout

```
BrazilianSoccerMcp.sln
Directory.Build.props          # restricts the .NET 10 SDK's built-in
                               # Microsoft.Build.Tasks.Git to local-only
                               # config (avoids ~/.gitconfig access errors
                               # in sandboxed environments)
src/BrazilianSoccerMcp/
  Program.cs                   # entry point: loads CSVs, starts MCP loop
  Data/
    DataRepository.cs          # CSV loaders for all 6 files
    MatchRecord.cs             # normalized match model
    PlayerRecord.cs            # player model
    TeamNameNormalizer.cs      # accent/suffix/punctuation normalization
  Services/
    MatchService.cs            # match search + head-to-head
    TeamService.cs             # team statistics
    PlayerService.cs           # FIFA player queries + grouping
    CompetitionService.cs      # standings, biggest victories, averages
  Mcp/
    McpServer.cs               # JSON-RPC 2.0 over stdio
    ToolRegistry.cs            # MCP tool catalogue + argument parsing
tests/BrazilianSoccerMcp.Tests/
  DataFixture.cs               # shared collection fixture (loads real CSVs)
  MatchQueryBddTests.cs        # Given/When/Then scenarios
  TeamStatsBddTests.cs
  PlayerQueryBddTests.cs
  CompetitionBddTests.cs
  McpProtocolBddTests.cs
```

## Exposed MCP Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Filter matches by team, opponent, competition, season and date range |
| `head_to_head` | Wins/draws/losses + match list between two teams |
| `team_stats` | Aggregate W/D/L and goals for a team (season/competition/venue filters) |
| `search_teams` | Discover canonical team spellings matching a name fragment |
| `search_players` | Search FIFA players by name, nationality, club, position, min overall |
| `players_by_club` | Group players by club for a filter (e.g. Brazilian players) |
| `standings` | Computed competition standings for a season (3-1-0 points) |
| `biggest_victories` | Largest-margin victories in the dataset |
| `match_averages` | Average goals/match + home/away/draw win rates |
| `seasons` | List seasons present for a competition |

## Build

```bash
dotnet build
```

## Run as an MCP server (stdio)

The server reads JSON-RPC requests from stdin, one per line, and writes one
JSON-RPC response per line to stdout:

```bash
dotnet run --project src/BrazilianSoccerMcp
```

Example handshake + tool call:

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"teamA":"Flamengo","teamB":"Fluminense"}}}' \
  | dotnet run --project src/BrazilianSoccerMcp
```

### Registering with Claude Desktop

Add an entry to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "/absolute/path/to/src/BrazilianSoccerMcp", "--no-build"]
    }
  }
}
```

## Tests

The test suite uses **xUnit** with BDD-style Given/When/Then scenarios
(see `tests/BrazilianSoccerMcp.Tests/*.cs`). The shared `DataFixture`
collection loads the real Kaggle CSVs once for the whole run.

```bash
dotnet test
```

Current state: **23 / 23 passing**.

## Data Quality Notes

- **Team name normalization**: `"Palmeiras-SP"`, `"Palmeiras"` and accented
  variants all collapse to the same internal key (`palmeiras`) so cross-file
  joins work. The original raw name is preserved on every `MatchRecord`.
- **Date formats**: both ISO (`yyyy-MM-dd HH:mm:ss`, `yyyy-MM-dd`) and the
  Brazilian `dd/MM/yyyy` used by the historical file are handled.
- **Character encoding**: all CSVs are read as UTF-8 and accented names
  (São Paulo, Grêmio, Avaí) are preserved.
- **FIFA dataset caveat**: the bundled FIFA 19 snapshot mostly contains
  European clubs, so queries for "players at Flamengo" return empty.
  Queries by nationality ("Brazilian players at Real Madrid") work fine and
  are covered by tests.
