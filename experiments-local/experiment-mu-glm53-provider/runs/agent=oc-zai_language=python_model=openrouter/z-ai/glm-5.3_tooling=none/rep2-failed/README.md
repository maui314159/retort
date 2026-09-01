# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language
questions about Brazilian soccer — players, teams, matches and
competitions — over the Kaggle datasets in `data/kaggle/`.

## What was built

| File | Purpose |
|------|---------|
| `models.py` | `Match` / `Player` / `TeamRecord` domain models |
| `normalize.py` | Team-name canonicalization (alias table + suffix rules), multi-format date parsing, competition aliases, derby catalog |
| `data_loader.py` | Loads all 6 CSVs, deduplicates fixtures across sources, builds in-memory indexes; learns extra team-name aliases from duplicate fixtures |
| `stats.py` | Team records, head-to-head, standings, aggregates, biggest wins, derbies |
| `server.py` | The MCP server (16 tools) + stdio/HTTP entry point |
| `test_*.py` | BDD Given/When/Then pytest suite (100 scenarios) |
| `e2e_stdio_check.py` | Manual end-to-end check that drives the server over stdio JSON-RPC |

## Running

```bash
pip install -r requirements.txt

# stdio transport (default, for Claude Desktop / MCP clients)
python server.py

# HTTP transport
python server.py --transport streamable-http --port 8321
```

Example client registration (Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/path/to/this/repo/server.py"]
    }
  }
}
```

## Data pipeline highlights

- **Unified match set** — the five match files overlap heavily (Série A
  2012-2019 exists in three files). Fixtures are deduplicated by
  `(competition, date±1, home, away)` and `(competition, season, round)`;
  the 2022 Série A rows that the Brasileirão file lists without scores are
  filled in from the extended-stats file. Result: 16,745 unique matches,
  and every season table reproduces the historical record (2019 Flamengo
  90 pts, 2020 champion Flamengo, 2021 Atlético-MG 84 pts, 2022 Palmeiras
  81 pts, correct relegated teams, ...).
- **Team-name normalization** — every spelling variant maps to one
  canonical key: `Palmeiras-SP` = `Palmeiras` = `SE Palmeiras`;
  `Atlético-PR` = `Athletico Paranaense` = `Athletico`;
  `Sport Club do Recife` = `Sport-PE`; `A.s.a.` = `Asa`; `Nacional (URU)`
  ≠ `Nacional (PAR)`. A second-phase loader *learns* additional aliases
  directly from duplicate fixtures (74+ aliases discovered), so small
  clubs like `AE Altos`/`Altos-PI` merge automatically.
- **FIFA licensing gap** — the FIFA snapshot has no Flamengo, Palmeiras,
  Corinthians, São Paulo or Vasco players; club tools detect this and say
  so instead of failing.

## MCP tools (16)

`get_dataset_overview`, `resolve_team`, `list_teams`, `search_matches`,
`get_head_to_head`, `get_team_stats`, `search_players`,
`get_player_details`, `get_club_players`, `get_standings`,
`get_competition_info`, `get_competition_finals`,
`get_aggregate_statistics`, `get_biggest_wins`, `get_best_records`,
`get_derby_matches`

Every tool returns `{"summary": <human-readable answer>, "data": <structured rows>}`.
Ambiguous names ("Atletico") return a candidate list instead of guessing.

## Example answers

```
> get_standings("Brasileirão", 2019)
1. Flamengo - 90 pts (28W, 6D, 4L) - Champion
2. Santos - 74 pts (22W, 8D, 8L)
...

> get_head_to_head("Flamengo", "Fluminense")
- Meetings: 44, Flamengo 18 wins, Fluminense 14 wins, 12 draws

> get_competition_finals("Copa Libertadores")
- 2020: won by Palmeiras (Palmeiras 1-0 Santos)
- 2019: won by Flamengo (Flamengo 2-1 River Plate)
```

## Testing

```bash
python -m pytest            # 100 BDD GWT scenarios pass
python e2e_stdio_check.py   # drives the server over stdio JSON-RPC
```

The BDD suite covers: match queries (team/opponent/season/date/stage),
team records and home/away splits, head-to-head, player search and
profiles, standings verified against real history, cup finals with
two-leg aggregates, aggregate statistics, biggest wins, derbies, team-name
normalization, dataset coverage (all 6 CSVs, 22 sample questions) and the
MCP protocol layer, plus the TASK.md performance budget (simple lookups
< 2s, aggregates < 5s).

## Data sources

All datasets are pre-downloaded in `data/kaggle/` (see licenses in the
original Kaggle pages, linked in TASK.md): Brasileirão / Copa do Brasil /
Libertadores matches (CC BY 4.0), extended match statistics (CC0),
historical Brasileirão 2003-2019 (CC BY 4.0), FIFA players (Apache 2.0).
