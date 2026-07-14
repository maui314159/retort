# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv


## Implementation

### MCP Server

TypeScript MCP server (`@modelcontextprotocol/sdk` v1.29.0) over stdio transport.
9 query tools mapped to Brazilian soccer data:

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, competition, season, date range |
| `get_team_stats` | Team W/L/D record, home/away split, per-competition breakdown |
| `get_head_to_head` | Compare two teams: wins, goals, match history |
| `search_players` | Search FIFA player DB by name, nationality, club, position, rating |
| `get_standings` | Calculate league standings from match results |
| `get_biggest_wins` | Largest goal-difference victories |
| `get_competition_stats` | Aggregate stats: avg goals, home/away rates, top scorers |
| `get_best_away_teams` | Teams with best away win records |
| `get_server_info` | Dataset metadata, match/player counts, available competitions |

### Data Processing

- **Team name normalization**: strips state suffixes (`-SP`, `-RJ`), handles accents (`Grêmio` → `gremio`), removes parenthetical asides
- **Multi-format date parsing**: ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`), Brazilian (`29/03/2003`)
- **UTF-8**: full support for Brazilian Portuguese characters
- **Competition mapping**: standardizes names across 5 match datasets (`brasileirao`, `copa_do_brasil`, `libertadores`)

### Stats

- 23,954 matches across Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C
- 18,207 FIFA players
- Seasons: 2003-2023

### Usage

```bash
npm install
npm run build
npm start          # runs MCP server over stdio
npm test           # 38 BDD tests
```

Configure in an MCP client (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/path/to/brazilian-soccer-mcp"
    }
  }
}
```