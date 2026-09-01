# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server exposing a knowledge graph of
Brazilian soccer: **23,954 matches** across five datasets (2003-2023) plus
the **18,207-player** FIFA database, queryable in natural language through
18 typed tools.

Implements `TASK.md` / `brazilian-soccer-mcp-guide.md` in full: match,
team, player, competition and statistical queries; team-name normalization
across inconsistent sources; BDD GWT-structured pytest suite.

## Quick start

```bash
# with the bundled venv
source venv/bin/activate          # python 3.12, mcp + pytest installed
pytest                            # 126 BDD scenarios, ~3s

# run the MCP server (stdio transport)
python server.py                  # or: brazilian-soccer-mcp after `pip install .`
```

Register it with any MCP client (Claude Desktop, opencode, ...):

```json
{ "mcpServers": { "brazilian-soccer": { "command": "python", "args": ["/path/to/repo/server.py"] } } }
```

## Tools (18)

| Area | Tools |
|------|-------|
| Matches | `search_matches` (team/opponent/competition/season/date-range/stage), `head_to_head`, `last_match`, `derby_matches` (Fla-Flu, Gre-Nal, Choque-Rei, ...) |
| Teams | `team_record` (competition/season/venue splits), `team_profile` (cross-file view), `list_teams`, `resolve_team` (spelling disambiguation) |
| Players | `find_players` (name/club/nationality/position/rating), `top_players`, `players_at_club` |
| Competitions | `standings` (computed tables, home/away variants), `champion` (league or cup aggregate), `bracket`, `competition_info` |
| Statistics | `season_averages`, `biggest_wins`, `match_statistics` (corners/shots/attacks/half-time) |

Every tool returns JSON-serializable dicts with summary blocks, totals and
caveats (e.g. incomplete-season notes). Free-text team and competition
names are accepted in any spelling the sources use ("Flamengo",
"Flamengo-RJ", "Athletico Paranaense - PR", "serie a", "CdB", ...).

## Architecture

```
brazilian_soccer_mcp/
  normalize.py  # accent folding, date/goal parsing, team aliases, competition resolution
  models.py     # Match / Player / Club / StandingRow dataclasses
  registry.py   # club knowledge graph: every spelling -> one club entity
  dataset.py    # loads the six CSVs, builds the deduplicated canonical index
  service.py    # all query logic (pure functions over the dataset)
  server.py     # FastMCP wiring + stdio entry point
server.py       # thin launcher for MCP clients
tests/          # BDD GWT pytest suites + Gherkin .feature counterparts
```

### Data-quality decisions

The five match files overlap and disagree, so the pipeline assembles a
**canonical index** before any query runs:

- **One authoritative source per (competition, season)**: dedicated files
  win (Brasileirão 2012-2022, Copa do Brasil 2012-2021, Libertadores),
  then the historical 2003-2019 file (Serie A 2003-2011), then
  BR-Football (Serie A 2023, Serie B/C always). Naive concatenation would
  double-count every 2012-2019 fixture; dates misalign ~10% between
  sources, so per-season source selection is the only safe dedup.
- **Club identity across spellings**: `Palmeiras-SP`, `Palmeiras`,
  `Athletico Paranaense - PR`, `Atletico-PR` and `Sport Club do Recife`
  all map to one club via accent folding, UF-state extraction and an alias
  table. State-less spellings merge into the dominant same-base club
  (Libertadores "Flamengo" → Flamengo-RJ), while genuinely distinct clubs
  (Botafogo-RJ vs -PB, América-MG vs -RN) stay apart. The Argentine
  River Plate is explicitly kept separate from River Plate-SE.
- **Honest gaps**: unscored placeholder rows ("NA" goals: 2022 final
  round, 2021 cup rounds, the abandoned 2015 Boca x River Superclásico)
  are retained but excluded from statistics; standings report
  completeness (e.g. 2023 Serie A: 377 of 380 matches); penalty-decided
  cup finals report "winner not determinable from scores". The FIFA
  source omits several Brazilian club rosters (Flamengo, Palmeiras,
  Corinthians, São Paulo) — roster queries say so instead of erroring.
- **Extended statistics** (corners/shots/attacks/half-time) are joined
  from BR-Football onto canonical matches by (date, clubs) where possible.

Validated against known history: 2019 champion Flamengo 90 pts (28W-6D-4L)
with Santos above Palmeiras on the wins tiebreaker, 2019/2020/2021
relegation zones, 2021 champion Atlético-MG (84 pts), 2022 Serie B
champion Cruzeiro, Libertadores 2018/2019 winners.

### Performance

The dataset loads once (~1-2 s) and all queries run in-memory over the
canonical index, meeting the TASK.md targets (<2 s lookups, <5 s
aggregates) with large margins — asserted in `tests/test_statistics.py`.

## Testing

BDD GWT-structured pytest (`tests/test_*.py`, one Given/When/Then per
test, commented as such) with executable-adjacent Gherkin documentation in
`tests/features/*.feature`. The suite covers the exact scenarios sketched
in TASK.md plus ~50 more: file coverage, dedup, normalization, every
query category, data-gap honesty, JSON-serializability, MCP stdio JSON-RPC
round trip, and performance budgets.

```bash
venv/bin/python -m pytest tests/          # 126 passed
venv/bin/ruff check brazilian_soccer_mcp/ server.py tests/
```

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
