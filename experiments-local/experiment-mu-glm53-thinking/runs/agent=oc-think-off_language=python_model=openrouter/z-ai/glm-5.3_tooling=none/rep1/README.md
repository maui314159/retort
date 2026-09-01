# Brazilian Soccer MCP Server

MCP server exposing the Kaggle Brazilian soccer datasets (matches, players) as
query tools. Implements the spec in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Layout

- `server.py` — MCP server (8 tools). Run: `./venv/bin/python server.py` (stdio)
  or `./venv/bin/python server.py --http` (streamable HTTP, port 8000).
- `brazilian_soccer/loader.py` — CSV loading, team-name normalization
  (handles "Palmeiras-SP" vs "Palmeiras" vs "SE Palmeiras", distinct
  Atletico-MG/PR/GO clubs), multi-format date parsing, UTF-8 names.
- `brazilian_soccer/analysis.py` — match search, team stats, head-to-head,
  standings, biggest wins, goal averages, player search.
- `tests/test_soccer.py` — BDD-style pytest suite (25 scenarios).
- `data/kaggle/` — the six source CSVs.

## Tools

`search_matches`, `get_team_stats`, `compare_head_to_head`, `get_standings`,
`get_biggest_wins`, `get_average_goals`, `find_players`, `brazilian_clubs`

## Run tests

```bash
./venv/bin/python -m pytest tests -q
```
