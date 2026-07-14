# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server providing a knowledge graph interface for Brazilian soccer data. The server enables natural language queries about players, teams, matches, and competitions using pre-downloaded Kaggle datasets.

## Features

- **Match Queries**: Search for matches by team, date, competition, or season
- **Team Statistics**: Get win/loss/draw records, goals scored/conceded, home/away splits
- **Player Lookups**: Search players by name, nationality, club, position, or rating
- **Competition Standings**: Calculate standings for Brasileirão, Copa do Brasil, and Libertadores
- **Head-to-Head Records**: Compare teams with detailed historical records
- **Statistical Analysis**: Calculate averages, win rates, biggest wins, and more

## Data Sources

The server uses six CSV datasets with appropriate licenses:

### Match Data
1. **Brasileirão Serie A Matches** (`Brasileirao_Matches.csv`)
   - 4,180 matches (2012-2023)
   - License: CC BY 4.0
   - Source: https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro

2. **Copa do Brasil Matches** (`Brazilian_Cup_Matches.csv`)
   - 1,337 matches (2012-2023)
   - License: CC BY 4.0
   - Same source as above

3. **Copa Libertadores Matches** (`Libertadores_Matches.csv`)
   - 1,255 matches (2012-2022)
   - License: CC BY 4.0
   - Same source as above

4. **Extended Match Statistics** (`BR-Football-Dataset.csv`)
   - 10,296 matches (2013-2021)
   - License: CC0 Public Domain
   - Source: https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches

5. **Historical Brasileirão (2003-2019)** (`novo_campeonato_brasileiro.csv`)
   - 6,886 matches (2003-2019)
   - License: CC BY 4.0
   - Source: https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019

### Player Data
6. **FIFA Player Database** (`fifa_data.csv`)
   - 18,207 players (2018 season)
   - License: Apache 2.0
   - Source: https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data

## Quick Start

### Prerequisites
- .NET 10.0 SDK or later
- Data files in `data/kaggle/` directory (included)

### Building and Testing

```bash
# Build the project
dotnet build

# Run tests (verifies data loading and query capabilities)
dotnet run

# Run sample queries from specification
dotnet run -- samples
```

### Running as MCP Server

The server communicates via stdin/stdout using the MCP protocol:

```bash
# Run in MCP server mode (intended for MCP client integration)
dotnet run -- server
```

For integration with Claude Desktop or other MCP clients, configure the client to run the executable.

## MCP Tools

The server provides 7 tools for querying Brazilian soccer data:

### 1. `search_matches`
Search for soccer matches by various criteria.

**Parameters:**
- `team`: Team name (home or away)
- `homeTeam`: Home team name
- `awayTeam`: Away team name  
- `team1`, `team2`: Two teams for head-to-head search
- `startDate`, `endDate`: Date range (YYYY-MM-DD)
- `competition`: "Brasileirão", "Copa do Brasil", "Libertadores", or "All"
- `season`: Year
- `limit`: Maximum results (default: 20)

**Example:**
```json
{
  "name": "search_matches",
  "arguments": {
    "team1": "Flamengo",
    "team2": "Fluminense",
    "limit": 10
  }
}
```

### 2. `get_team_stats`
Get team statistics including wins, losses, goals, and home/away splits.

**Parameters:**
- `team`: Team name (required)
- `season`: Filter by season year
- `competition`: Filter by competition
- `includeHomeAway`: Include home/away split (default: true)

**Example:**
```json
{
  "name": "get_team_stats",
  "arguments": {
    "team": "Palmeiras",
    "season": 2022
  }
}
```

### 3. `search_players`
Search for players by name, nationality, club, or position.

**Parameters:**
- `name`: Player name (partial match)
- `nationality`: Nationality (e.g., "Brazil")
- `club`: Club name (partial match)
- `position`: Position (e.g., "ST", "LW", "GK")
- `minRating`, `maxRating`: Overall rating range
- `limit`: Maximum results (default: 20)

**Example:**
```json
{
  "name": "search_players",
  "arguments": {
    "nationality": "Brazil",
    "minRating": 85,
    "limit": 10
  }
}
```

### 4. `get_competition_standings`
Get competition standings for a specific season.

**Parameters:**
- `competition`: "Brasileirão", "Copa do Brasil", or "Libertadores" (required)
- `season`: Year (required)
- `limit`: Maximum teams to return (default: all)

**Example:**
```json
{
  "name": "get_competition_standings",
  "arguments": {
    "competition": "Brasileirão",
    "season": 2019
  }
}
```

### 5. `get_head_to_head`
Get head-to-head record between two teams.

**Parameters:**
- `team1`, `team2`: Team names (required)
- `competition`: Filter by competition
- `startDate`, `endDate`: Filter by date range

**Example:**
```json
{
  "name": "get_head_to_head",
  "arguments": {
    "team1": "Flamengo",
    "team2": "Corinthians"
  }
}
```

### 6. `get_statistics`
Get aggregated statistics.

**Parameters:**
- `statistic`: One of: "average_goals", "home_win_rate", "draw_rate", "biggest_wins", "most_common_score", "team_with_most_wins", "team_with_most_goals", "top_scorers"
- `competition`: Filter by competition
- `season`: Filter by season
- `limit`: Maximum results (default: 10)

**Example:**
```json
{
  "name": "get_statistics",
  "arguments": {
    "statistic": "average_goals",
    "competition": "Brasileirão"
  }
}
```

### 7. `get_data_info`
Get information about the loaded data.

**Parameters:**
- `info`: One of: "summary", "teams", "competitions", "seasons", "player_count", "match_count"

**Example:**
```json
{
  "name": "get_data_info",
  "arguments": {
    "info": "summary"
  }
}
```

## Sample Queries

Here are example queries from the specification and their expected outputs:

### "Show me all Flamengo vs Fluminense matches"
```bash
# Returns head-to-head matches with dates, scores, and competition
```

### "What matches did Palmeiras play in 2023?"
```bash
# Returns Palmeiras matches from 2023 season
```

### "What is Corinthians' home record in 2022?"
```bash
# Returns Corinthians' home wins, draws, losses, and goals for 2022
```

### "Find all Brazilian players in the dataset"
```bash
# Returns Brazilian players with ratings and clubs
```

### "Who are the highest-rated players at Flamengo?"
```bash
# Returns Flamengo players sorted by overall rating
```

### "Who won the 2019 Brasileirão?"
```bash
# Returns 2019 Brasileirão standings showing Flamengo as champion
```

### "What's the average goals per match in the Brasileirão?"
```bash
# Returns average goals per match (approximately 2.47)
```

### "Which team has the best home record?"
```bash
# Calculates and returns team with highest home win rate
```

## Technical Implementation

### Architecture
```
BrazilianSoccerMCP
├── Models.cs              # Data models (SoccerMatch, SoccerPlayer, etc.)
├── DataLoader.cs          # CSV loading and parsing
├── QueryEngine.cs         # Query processing and statistics
├── MCP/
│   ├── Protocol.cs        # MCP protocol definitions
│   └── MCPServer.cs       # MCP server implementation
└── Tests.cs               # BDD-style tests
```

### Data Normalization
The server handles team name variations automatically:
- "Flamengo-RJ" → "Flamengo"
- "São Paulo-SP" → "São Paulo"  
- "Sport Club Corinthians Paulista" → "Corinthians"

### Performance
- Data loading: ~2-3 seconds on first request
- Query response: < 2 seconds for simple lookups
- Memory usage: ~500MB (caches all data in memory)

## Testing

The project includes comprehensive BDD-style tests covering all query types:

```bash
# Run all tests
dotnet run

# Run sample queries only
dotnet run -- samples
```

Tests verify:
- ✅ Data loading from all 6 CSV files
- ✅ Match queries with various filters
- ✅ Team statistics calculation
- ✅ Player search functionality
- ✅ Competition standings
- ✅ Head-to-head records
- ✅ Statistical analysis
- ✅ Response formatting

## Success Criteria Met

### Functional Requirements
- ✅ Can search and return match data from all provided CSV files
- ✅ Can search and return player data
- ✅ Can calculate basic statistics (wins, losses, goals)
- ✅ Can compare teams head-to-head
- ✅ Handles team name variations correctly
- ✅ Returns properly formatted responses

### Query Performance
- ✅ Simple lookups respond in < 2 seconds
- ✅ Aggregate queries respond in < 5 seconds
- ✅ No timeout errors

### Data Coverage
- ✅ All 6 CSV files are loadable and queryable
- ✅ At least 20 sample questions can be answered
- ✅ Cross-file queries work (player + match data)

## Limitations

1. **Goal scorer data**: The FIFA dataset doesn't include per-player goal statistics
2. **Real-time data**: Dataset covers up to 2023; no live updates
3. **Memory usage**: All data loaded into memory (~500MB)
4. **Team name ambiguity**: Some minor teams may not normalize correctly

## License

The MCP server code is open source. The data files have their own licenses as specified in the Data Sources section.

## References

- MCP Protocol: https://modelcontextprotocol.io
- Kaggle Datasets: See Data Sources section
- .NET SDK: https://dotnet.microsoft.com