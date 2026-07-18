# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a knowledge graph interface for Brazilian soccer data. Built in C# / .NET 10, it loads six Kaggle datasets (23,000+ matches, 18,000+ players) into memory and exposes structured query tools to any MCP-compatible LLM client (Claude, Copilot, etc.).

## What Was Built

- **MCP Server** (`src/BrazilianSoccerMcp/`) — A .NET console app using the official [ModelContextProtocol C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) (v1.4.1) over stdio transport. Exposes 10 tools covering all 5 spec capability categories.
- **BDD Test Suite** (`tests/BrazilianSoccerMcp.Tests/`) — 45 Given/When/Then tests (xUnit) verifying match queries, team stats, player search, standings, and data coverage across all 6 CSV files.

## Architecture

```
src/BrazilianSoccerMcp/
  Models/
    Match.cs              — Unified match record from 5 CSV sources
    Player.cs             — FIFA player subset
    TeamStats.cs          — Aggregated win/draw/loss + standings row
  Services/
    SoccerDataService.cs  — In-memory data store; loads all 6 CSVs, indexes by canonical team key
    TeamNameNormalizer.cs — Canonical key: strips state suffixes, accents, punctuation for cross-dataset matching
    DataPathResolver.cs   — Walks up from bin/ to find data/kaggle/
  Tools/
    MatchTools.cs         — FindMatches, GetTeamStats, CompareTeams
    SoccerTools.cs        — SearchPlayers, GetClubPlayers, GetStandings, GetChampion, GetAggregateStats, GetBiggestVictories, ListTeams
  Program.cs              — Host setup: stdio transport, DI, WithToolsFromAssembly
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `FindMatches` | Filter matches by team, opponent, competition, season, date range |
| `GetTeamStats` | Win/loss/draw record, goals, win rate (filterable by competition/season/home/away) |
| `CompareTeams` | Head-to-head record between two teams |
| `SearchPlayers` | Search FIFA database by name, nationality, club, position, rating |
| `GetClubPlayers` | List all players at a club |
| `GetStandings` | Computed league standings for a season |
| `GetChampion` | Champion team for a competition season |
| `GetAggregateStats` | Average goals, home/away win rates, draw rate |
| `GetBiggestVictories` | Largest goal-margin victories |
| `ListTeams` | All known team names (for discovery) |

## Data Coverage

All 6 Kaggle datasets are loaded and queryable:

| File | Records | Source |
|------|---------|--------|
| Brasileirao_Matches.csv | 4,180 | Brasileirão Serie A (2012–2022) |
| Brazilian_Cup_Matches.csv | 1,337 | Copa do Brasil (2012–2021) |
| Libertadores_Matches.csv | 1,255 | Copa Libertadores (2013–2022) |
| BR-Football-Dataset.csv | 10,296 | Extended stats (corners, shots, attacks) |
| novo_campeonato_brasileiro.csv | 6,886 | Historical Brasileirão (2003–2019) |
| fifa_data.csv | 18,207 | FIFA player database |

## Team Name Normalization

The datasets spell team names differently across files. The normalizer produces a canonical key that is:
- Lowercase, accent-free (Atlético → atletico)
- Punctuation-free (A.b.c. → abc)
- State/country suffix stripped (Palmeiras-SP → palmeiras, Barcelona-EQU → barcelona)
- Parenthetical qualifiers removed (Nacional (URU) → nacional)

This enables cross-dataset queries — searching "Palmeiras" matches all variants.

## Build & Test

```bash
dotnet build
dotnet test
```

## Run the MCP Server

```bash
dotnet run --project src/BrazilianSoccerMcp
```

The server runs over stdio. Connect from any MCP client (e.g. Claude Desktop) by adding to the client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "src/BrazilianSoccerMcp"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

## Testing Approach

BDD (Behavior-Driven Development) with Given/When/Then scenarios in xUnit:

- **MatchQueryBddTests** — Find matches between teams, by competition, by season; date/score/competition validation
- **TeamStatsBddTests** — Team statistics, home/away partition, standings, head-to-head, biggest victories
- **PlayerQueryBddTests** — Brazilian player search, name search, club roster, top-rated filtering
- **DataCoverageBddTests** — All 6 CSVs loaded, cross-file queries, name normalization, date/goal parsing
- **McpToolOutputBddTests** — Tool output formatting, performance (<2s), 20+ sample questions answered

## Data Sources

- [Kaggle Brazilian Soccer](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) (CC BY 4.0)
- [Brazilian Football Matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) (CC0)
- [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) (CC BY 4.0)
- [FIFA Players](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) (Apache 2.0)
