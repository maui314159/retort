# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that provides a knowledge graph interface for Brazilian soccer data. It enables natural language queries about players, teams, matches, and competitions using the provided datasets.

## Features

- **Match Queries**: Search matches by team, season, or competition.
- **Team Statistics**: Get win/loss/draw records and goals for a specific team.
- **Head-to-Head**: Compare two teams' historical matchup records.
- **Player Search**: Find players by name, nationality, club, or minimum overall rating.
- **Competition Standings**: Calculate league tables dynamically from match results.

## Data Sources

All datasets are included in `data/kaggle/` under open licenses:

1. **Brasileirão Serie A** (`Brasileirao_Matches.csv`) - CC BY 4.0
2. **Copa do Brasil** (`Brazilian_Cup_Matches.csv`) - CC BY 4.0
3. **Copa Libertadores** (`Libertadores_Matches.csv`) - CC BY 4.0
4. **Extended Match Statistics** (`BR-Football-Dataset.csv`) - CC0 Public Domain
5. **Historical Brasileirão 2003-2019** (`novo_campeonato_brasileiro.csv`) - CC BY 4.0
6. **FIFA Player Database** (`fifa_data.csv`) - Apache 2.0

## Installation

```bash
npm install
```

## Development

```bash
# Build TypeScript
npm run build

# Run tests
npm run test

# Start development server with watch mode
npm run dev
```

## Usage

### As an MCP Server

Configure your MCP client (e.g., Claude Desktop, Cursor, Zed) to use this server:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "npx",
      "args": ["tsx", "src/index.ts"],
      "cwd": "/path/to/this/directory"
    }
  }
}
```

Or after building:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/path/to/this/directory"
    }
  }
}
```

### Available Tools

1. `search_matches`: Find matches by team, season, or competition.
2. `get_team_statistics`: Get win/loss/draw records for a team.
3. `get_head_to_head`: Compare historical matchups between two teams.
4. `search_players`: Search the FIFA database by name, nationality, or club.
5. `get_competition_standings`: Calculate league standings for a given season.

## Example Queries

- "Show me all Flamengo vs Fluminense matches in 2023"
- "What is Palmeiras' home record in the 2022 Brasileirão?"
- "Find all Brazilian players with an overall rating above 85"
- "Who won the 2019 Brasileirão?"

## Architecture

- **TypeScript** with strict typing and ESM modules.
- **Zod** for runtime schema validation of tool inputs.
- **csv-parse** for efficient CSV parsing with UTF-8 support.
- **Team normalization** handles variations like "Palmeiras-SP", "SE Palmeiras", and "Sport Club Internacional" uniformly.

## Testing

The project includes BDD-style test scenarios validating:
- Data loading across all 6 CSV files
- Team name normalization edge cases
- Match filtering and head-to-head logic
- Team statistics aggregation