# Brazilian Soccer MCP Server

MCP (Model Context Protocol) server providing a knowledge graph interface for Brazilian soccer data across 6 CSV datasets.

## Overview

- **Data**: 23,954 matches + 18,207 FIFA players across 6 Kaggle datasets
- **Protocol**: MCP over stdio (`@modelcontextprotocol/sdk`)
- **Language**: TypeScript, Node.js 16+

## Data Sources

| Dataset | File | Records | License |
|---------|------|---------|---------|
| Brasileirão Serie A | `Brasileirao_Matches.csv` | 4,180 | CC BY 4.0 |
| Copa do Brasil | `Brazilian_Cup_Matches.csv` | 1,337 | CC BY 4.0 |
| Copa Libertadores | `Libertadores_Matches.csv` | 1,255 | CC BY 4.0 |
| Extended Stats | `BR-Football-Dataset.csv` | 10,296 | CC0 |
| Historical (2003-2019) | `novo_campeonato_brasileiro.csv` | 6,886 | CC BY 4.0 |
| FIFA Players | `fifa_data.csv` | 18,207 | Apache 2.0 |

## MCP Tools

### Match Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, season, competition, date range, round |
| `get_team_stats` | Wins, losses, draws, goals, win rate for a team |
| `get_head_to_head` | Head-to-head record between two teams |
| `get_standings` | League standings for a season (points, W/D/L, GF/GA) |
| `get_biggest_wins` | Biggest victories (GD >= 5) |
| `get_goal_averages` | Goals per match, home win rate, draw rate |
| `get_home_away_stats` | Home vs away performance for a team |

### Player Tools

| Tool | Description |
|------|-------------|
| `search_players` | Search by name, nationality, club, position, rating |
| `get_player_details` | Full stats for a specific player |
| `get_top_players` | Top-rated players, optionally filtered |
| `get_club_summaries` | Player counts and avg ratings by club |

## Build & Run

```bash
npm install
npm run build
npm start              # runs the MCP server on stdio
npm test               # runs integration tests (32 tests)
```

## MCP Client Configuration

Add to your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/path/to/brazilian-soccer-mcp/build/index.js"]
    }
  }
}
```

## Team Name Normalization

The server handles name variations across datasets:
- State suffixes: "Flamengo-RJ" → "Flamengo"
- Accents: "Sao Paulo" → "São Paulo"
- Full names: "Atlético Mineiro" → "Atlético-MG"
- Abbreviations: "EC Bahia" → "Bahia"
