# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server providing a knowledge graph interface for Brazilian soccer data. Built in C# with .NET 10.0, using the official `ModelContextProtocol` NuGet package.

## Quick Start

```bash
cd BrazilianSoccerMCP
dotnet run
```

The server starts on stdio and accepts MCP JSON-RPC requests.

## Architecture

- **BrazilianSoccerMCP/** - Main project
  - `Program.cs` - MCP server entry point with DI configuration
  - `Tools/SoccerTools.cs` - 12 MCP tools for match/team/player/competition/statistics queries
  - `Data/DataLoader.cs` - CSV loading with UTF-8, BOM handling, multi-format date parsing
  - `Data/TeamNormalizer.cs` - Team name normalization (state suffixes, accents, abbreviations)
  - `Models/` - 8 data records for all 6 CSV datasets + unified match model
- **BrazilianSoccerMCP.Tests/** - xUnit test project (35 tests, all passing)

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Search matches by team, season, competition, date range |
| `head_to_head` | Compare two teams with wins/losses/draws and match list |
| `team_statistics` | Team W/D/L record, goals, win rate |
| `team_home_record` | Home match statistics |
| `team_away_record` | Away match statistics |
| `search_players` | FIFA player database search by name, nationality, club, position |
| `team_players` | List players at a club |
| `competition_standings` | Calculated league table by season |
| `competition_winners` | List season champions |
| `biggest_wins` | Largest goal difference victories |
| `goals_per_match_average` | Average goals per match |
| `team_season_comparison` | Compare team across two seasons |

## Data Sources

Kaggle data (freely available with attribution):

| Dataset | License | Records |
|---------|---------|---------|
| Brasileirao_Matches.csv | CC BY 4.0 | 4,180 |
| Brazilian_Cup_Matches.csv | CC BY 4.0 | 1,337 |
| Libertadores_Matches.csv | CC BY 4.0 | 1,255 |
| BR-Football-Dataset.csv | CC0 Public Domain | 10,296 |
| novo_campeonato_brasileiro.csv | CC BY 4.0 | 6,886 |
| fifa_data.csv | Apache 2.0 | 18,207 |

## Data Quality Handling

- Team name normalization: strips state suffixes, handles accents, resolves abbreviations
- Multi-format date parsing: ISO, Brazilian, with/without time
- Null handling: "NA", "-", and empty fields treated as null
- UTF-8 with BOM auto-detection
