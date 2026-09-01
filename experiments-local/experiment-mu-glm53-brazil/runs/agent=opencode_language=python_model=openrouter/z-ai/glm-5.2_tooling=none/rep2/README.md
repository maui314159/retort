# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph-style
interface over Brazilian soccer data: matches, teams, players, competitions,
and statistics across six Kaggle CSV datasets.

## What was built

Implements the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md):

- **`brazilian_soccer_mcp/team_normalize.py`** — canonicalizes team names
  across the datasets' many spelling variants (`"Palmeiras-SP"`,
  `"Clube de Regatas do Flamengo"`, `"Atlético Mineiro"`, `"Nacional (URU)"`,
  ASCII `"Sao Paulo"` in BR-Football-Dataset, full Portuguese names in the
  historical Brasileirão, etc.) onto one stable lowercase ASCII key, with a
  hand-curated alias table plus an accent/noise-token fallback. Also exposes
  a curated derby table (Fla-Flu, Grenal, Derby Paulista, ...).
- **`brazilian_soccer_mcp/data_loader.py`** — loads and normalizes all six
  Kaggle CSVs into a single list of `Match` / `Player` dataclasses. Handles
  the heterogeneous date formats (ISO datetime, ISO date, Brazilian
  `DD/MM/YYYY`), the FIFA file's UTF-8 BOM, float-encoded goals
  (`"1.0"`), and missing/blank scores.
- **`brazilian_soccer_mcp/models.py`** — typed dataclasses for `Match`,
  `Player`, `TeamStats`, `Standing`, `HeadToHead`.
- **`brazilian_soccer_mcp/queries.py`** — the `QueryEngine` exposing the
  five required capability categories (match queries, team queries, player
  queries, competition queries, statistical analysis).
- **`brazilian_soccer_mcp/server.py`** — an MCP v2 (`mcp>=2.1`,
  `MCPServer`) stdio server registering **16 tools** that wrap the query
  engine. Each tool returns a JSON string payload.

## Data sources (in `data/kaggle/`)

| File | Records | License |
|------|---------|---------|
| `Brasileirao_Matches.csv` | 4,180 | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | Apache 2.0 |

## Tools exposed

`search_matches`, `head_to_head`, `team_statistics`, `competitions_for_team`,
`search_players`, `top_rated_by_nationality`, `top_rated_by_club`,
`list_competitions`, `standings`, `average_goals`, `biggest_wins`,
`best_record_by_venue`, `top_scorers_by_team`, `derbies_in_season`,
`list_teams`, `list_sources`.

## Install & run

```bash
./venv/bin/pip install -e .
./venv/bin/brazilian-soccer-mcp            # stdio MCP server
# or: python -m brazilian_soccer_mcp.server
```

The data directory defaults to `./data/kaggle`; override with
`BRAZILIAN_SOCCER_DATA_DIR=/path/to/csvs brazilian-soccer-mcp`.

### Connect from an MCP client

Add the server to your client config (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/abs/path/to/venv/bin/brazilian-soccer-mcp"
    }
  }
}
```

## Example queries (verified against the data)

- **Average goals per Brasileirão match** → `2.472` (home win rate ~49.6%)
- **2019 Brasileirão champion** → Flamengo (calculated from match results)
- **Fla-Flu head-to-head** → Flamengo 31 wins, Fluminense 25, 21 draws
  (flagged as a derby)
- **Top-rated Brazilians** → Neymar Jr (92), Thiago Silva / Marcelo /
  Coutinho / Casemiro (88)

## Testing

BDD-style pytest scenarios (Given/When/Then prose comments) cover all five
capability categories plus the normalization layer and the live MCP stdio
surface:

```bash
./venv/bin/python -m pytest tests/ -v
./venv/bin/ruff check brazilian_soccer_mcp/ tests/
```

60 tests pass; ruff is clean; coverage is 83% (the `server.py` module shows
0% only because its tools run inside a subprocess spawned by the stdio
client, so coverage instrumentation can't record them — they are exercised
end-to-end by `tests/test_server.py`).

## Project layout

```
brazilian_soccer_mcp/
  __init__.py          # public API: DataLoader, QueryEngine
  team_normalize.py    # canonical team keys + derby table
  data_loader.py       # CSV parsing for all 6 datasets
  models.py            # Match / Player / TeamStats / Standing dataclasses
  queries.py           # QueryEngine: the 5 capability categories
  server.py            # MCPServer (stdio) with 16 tools
tests/
  conftest.py          # session-scoped fixtures
  test_team_normalize.py
  test_data_loader.py
  test_queries.py
  test_server.py       # live stdio MCP client smoke tests
pyproject.toml         # build config + ruff + pytest config
requirements.txt
```

## License notes

Source code: Apache-2.0. Dataset licenses are per-file (see table above);
this project is for demo / non-commercial use as stated in the spec.
