# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server providing a knowledge-graph interface for Brazilian soccer data. Enables natural language queries about players, teams, matches, and competitions.

## Implementation

- **Language**: Python 3.12
- **Framework**: FastMCP (MCP Python SDK)
- **Transport**: stdio (default) or streamable HTTP (`--http`)

### Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server with 6 tool endpoints |
| `data_loader.py` | CSV loading, team name normalization, date parsing |
| `test_server.py` | 43 BDD-style pytest tests (all pass) |

### Tools

| Tool | Description |
|------|-------------|
| `soccer_search_matches` | Search matches by team, opponent, competition, season, date range, stage |
| `soccer_team_stats` | Team W/D/L record, goals for/against, win rate (home/away split) |
| `soccer_head_to_head` | Head-to-head record between two teams with recent match history |
| `soccer_search_players` | FIFA player search by name, nationality, club, position, rating |
| `soccer_competition_standings` | Standings table from match results (3 pts win, 1 pt draw) |
| `soccer_stats_analysis` | Averages, biggest wins, home/away records, goal trends, top scorers |

### Data Coverage

All 6 bundled Kaggle datasets loaded and queryable:
- **23,954** normalized match records across Brasileirão, Copa do Brasil, Libertadores, Serie A/B/C
- **18,207** FIFA player records
- **522** unique teams with normalized naming across datasets
- Seasons: 2003–2022 (Brasileirão), 2012–2022 (Copa do Brasil, Libertadores), plus extended BR-Football

### Team Name Normalization

Handles variations across datasets:
- State suffixes: `Palmeiras-SP` → `Palmeiras`
- Accents: `São Paulo` ↔ `sao paulo`
- Athletico/Atlético variants: `Athletico Paranaense` → `Athletico-PR`
- Full names: `Sport Club Corinthians Paulista` fragments

## Usage

```bash
# Install dependencies
pip install mcp pandas pydantic pytest pytest-asyncio

# Run server (stdio transport)
python server.py

# Run server (HTTP transport)
python server.py --http

# Run tests
python -m pytest test_server.py -v
```

## Specification

See `brazilian-soccer-mcp-guide.md` (also at `TASK.md`) for full requirements.

## Data Sources

All datasets are pre-downloaded from Kaggle under their respective open licenses (CC BY 4.0, CC0, Apache 2.0). See `data/kaggle/` directory.
