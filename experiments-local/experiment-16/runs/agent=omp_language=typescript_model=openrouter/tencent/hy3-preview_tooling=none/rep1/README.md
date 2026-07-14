# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that provides a knowledge graph interface for Brazilian soccer data. Enables natural language queries about players, teams, matches, and competitions using the provided datasets.

## Features

- **Match Queries**: Find matches by team, date range, competition, or season
- **Team Statistics**: Get comprehensive team stats including wins, losses, goals, and win rates
- **Player Search**: Search players by name, nationality, club, position, or rating
- **Head-to-Head**: Get head-to-head records between two teams
- **Competition Standings**: Calculate standings from match results
- **Statistical Analysis**: Get averages, win rates, and biggest wins

## Installation

```bash
npm install
npm run build
```

## Usage

### Running the Server

```bash
npm start
```

The server runs on stdio transport and can be connected to any MCP-compatible client.

### Connecting to Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/path/to/dist/index.js"]
    }
  }
}
```

### Available Tools

1. **find_matches_by_team** - Find matches for a specific team or between two teams
2. **get_team_stats** - Get comprehensive team statistics
3. **search_players** - Search for players with various filters
4. **get_head_to_head** - Get head-to-head record between two teams
5. **get_competition_standings** - Calculate competition standings by season
6. **get_statistics** - Get statistical analysis
7. **find_matches_by_date** - Find matches within a date range

## Sample Queries

### Simple Lookups

- "When did Flamengo last play Corinthians?"
- "What was the score of the Flamengo vs Fluminense match in 2023?"
- "Who is Gabriel Barbosa?" (searches FIFA player data)

### Team Queries

- "What is Corinthians' home record in 2022?"
- "Which team scored the most goals in Serie A 2023?"
- "Compare Palmeiras and Santos head-to-head"

### Player Queries

- "Find all Brazilian players in the dataset"
- "Who are the highest-rated players at Flamengo?"
- "Show me all forwards from São Paulo FC"

### Competition Queries

- "Who won the 2019 Brasileirão?"
- "Show the 2018 Copa Libertadores bracket"
- "Which teams were relegated in 2020?"

### Statistical Analysis

- "What's the average goals per match in the Brasileirão?"
- "Which team has the best away record?"
- "Show me the biggest wins in the dataset"

## Data Sources

The following datasets are included in `data/kaggle/`:

1. **Brasileirão Serie A Matches** (4,180 matches)
   - Source: [Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
   - License: CC BY 4.0

2. **Copa do Brasil Matches** (1,337 matches)
   - Source: [Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
   - License: CC BY 4.0

3. **Copa Libertadores Matches** (1,255 matches)
   - Source: [Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
   - License: CC BY 4.0

4. **BR Football Dataset** (10,296 matches)
   - Source: [Kaggle](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)
   - License: CC0 Public Domain

5. **Historical Brasileirão (2003-2019)** (6,886 matches)
   - Source: [Kaggle](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)
   - License: CC BY 4.0

6. **FIFA Player Database** (18,207 players)
   - Source: [Kaggle](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)
   - License: Apache 2.0

## Data Quality Notes

### Team Name Variations

The datasets use different naming conventions:
- With state suffix: "Palmeiras-SP", "flamengo-RJ"
- Without suffix: "Palmeiras", "flamengo"
- Full names: "Sport Club Corinthians Paulista"

The server normalizes team names for consistent matching.

### Date Formats

The server handles multiple date formats:
- ISO format: "2023-09-24"
- Brazilian format: "29/03/2003"
- With time: "2012-05-19 18:30:00"

## Running Tests

```bash
npm test
```

The test suite verifies:
- Server initialization
- All 7 tools are registered
- Match data queries
- Player data queries
- Team statistics calculation
- Head-to-head records
- Team name normalization
- Response formatting
- Data loading from all CSV files
- Query performance (< 2 seconds for simple lookups)

## License

MIT

## Acknowledgments

- Data provided by Ricardo Mattos, Cue Cacuela, Macedo J. Leo, and Youssef El Badry via Kaggle
- Built with the [Model Context Protocol SDK](https://modelcontextprotocol.io)
