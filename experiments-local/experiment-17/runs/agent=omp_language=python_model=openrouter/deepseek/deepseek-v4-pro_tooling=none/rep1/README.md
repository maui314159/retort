# Brazilian Soccer MCP Server

MCP (Model Context Protocol) server providing a knowledge graph interface for Brazilian soccer data. Enables natural language queries about players, teams, matches, and competitions using 6 Kaggle datasets totaling ~42,000 matches and ~18,000 players.

## Implementation

Built with the [MCP Python SDK](https://modelcontextprotocol.io) (FastMCP), pandas for data processing, and pytest for BDD-style testing.

### Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server entry point — 13 tools via FastMCP |
| `data_loader.py` | CSV loading, team name normalization, date parsing |
| `query_engine.py` | Core query logic for all tool implementations |
| `test_server.py` | 42 BDD-style pytest tests (Given/When/Then) |
| `pyproject.toml` | Project config with dependencies |

### MCP Tools

| Tool | Description |
|------|-------------|
| `tool_search_matches` | Search matches by team, opponent, competition, season, date range |
| `tool_get_team_stats` | Team statistics: wins, losses, draws, goals, home/away records |
| `tool_search_players` | Search FIFA player database by name, nationality, club, position, rating |
| `tool_get_head_to_head` | Head-to-head comparison between two teams |
| `tool_get_standings` | League standings calculated from match results (3-1-0 points) |
| `tool_get_season_summary` | Season summary with champion, stats, and top standings |
| `tool_get_average_goals` | Average goals per match, home/away/draw rates |
| `tool_get_biggest_wins` | Biggest victories by goal difference |
| `tool_get_top_brazilian_players` | Highest-rated Brazilian players |
| `tool_get_players_by_club` | Players for a specific club sorted by rating |
| `tool_get_highest_scoring_teams` | Teams with most goals scored |
| `tool_get_team_performance_trend` | Team performance by season |
| `tool_get_data_summary` | Overview of loaded datasets |

### Team Name Normalization

Handles cross-dataset naming inconsistencies:
- State suffixes: "Flamengo-RJ" → "Flamengo"
- Accents: "Grêmio" ↔ "Gremio"
- Full names: "Sport Club Corinthians Paulista" → "Corinthians"
- Parentheticals: "Nacional (URU)" → "Nacional"
- ~800 canonical team entries with alias mappings

### Date Parsing

Supports: ISO (`2023-09-24`), Brazilian (`29/03/2003`), datetime (`2012-05-19 18:30:00`).

### Running

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the MCP server (stdio transport)
python server.py

# Run tests
pytest test_server.py -v
```

### Configuration (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/brazilian-soccer-mcp"
    }
  }
}
```

## Data Sources

| Dataset | Matches/Players | License |
|---------|----------------|---------|
| Brasileirao_Matches.csv | 4,180 | CC BY 4.0 |
| Brazilian_Cup_Matches.csv | 1,337 | CC BY 4.0 |
| Libertadores_Matches.csv | 1,255 | CC BY 4.0 |
| BR-Football-Dataset.csv | 10,296 | CC0 Public Domain |
| novo_campeonato_brasileiro.csv | 6,886 | CC BY 4.0 |
| fifa_data.csv | 18,207 | Apache 2.0 |

Sources: [Kaggle - Jogos do Campeonato Brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), [Brazilian Football Matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), [FIFA Players](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)

## Specification

See [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md) for the full specification.