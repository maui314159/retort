# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that
exposes a knowledge-graph interface over Brazilian soccer data. An LLM client
can call its tools to answer natural-language questions about matches, teams,
players, competition standings and aggregate statistics, drawn from six
pre-downloaded Kaggle datasets (~16.8k deduplicated matches + 18.2k FIFA
players).

Specification: `brazilian-soccer-mcp-guide.md` (also mirrored in `TASK.md`).

## What was built

A pure-Python package, `brazilian_soccer_mcp/`, layered bottom-up so the query
logic is testable without the protocol:

| Module | Responsibility |
|--------|----------------|
| `normalize.py` | Team-name and date normalisation. Folds accents/case/punctuation and resolves club spellings to one canonical key via a curated alias table (see below). Parses ISO, ISO+time and Brazilian `DD/MM/YYYY` dates. |
| `data_loader.py` | Reads the six CSVs into one **unified, deduplicated** match frame plus a players frame (`KnowledgeBase`). Maps every source onto logical competitions and drops cross-file duplicates, keeping the most complete row. |
| `queries.py` | Pure, JSON-returning query/aggregation functions (matches, team records, head-to-head, player search, standings, statistics, rankings). |
| `server.py` | Thin FastMCP adapter exposing the query layer as 10 MCP tools. |

### Data unification & normalisation

The five match files disagree on column names, ordering, dtypes, date formats
and even which competition a row belongs to. Notably:

- Série A 2012–2019 appears in **three** files, so matches are deduplicated on
  `(competition, season, home_canon, away_canon)` to avoid triple-counting
  standings and averages.
- Team names vary across files — `Flamengo` / `Flamengo-RJ` / `Flamengo RJ`,
  `Vasco` / `Vasco da Gama-RJ`, `Atletico Mineiro` / `Atletico-MG`. The
  two-letter state suffix is sometimes redundant (`Botafogo-RJ`) and sometimes
  the only discriminator (`Atletico-MG` vs `Atletico-GO` vs `Athletico-PR`),
  so normalisation resolves curated aliases **before** stripping a redundant
  state code. This is what makes the 2019 standings come out correctly
  (Flamengo champion, 90 pts, 20 teams, 38 games each).

### MCP tools

`find_matches`, `team_record`, `compare_teams`, `find_players`,
`players_by_club`, `league_standings`, `competition_statistics`,
`biggest_wins`, `best_team_record`, `list_competitions` — one or more per
capability area in the spec (match / team / player / competition / statistics).

## Running

```bash
pip install -r requirements.txt      # or: pip install -e .
python -m brazilian_soccer_mcp.server   # serves MCP over stdio
# or, after install:
brazilian-soccer-mcp
```

The data directory is auto-detected (`./data/kaggle`); override with the
`BR_SOCCER_DATA_DIR` environment variable.

### Example MCP client call

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    params = StdioServerParameters(command="python3", args=["-m", "brazilian_soccer_mcp.server"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("league_standings", {"competition": "Brasileirão", "season": 2019, "top_n": 3})
            print(res.structuredContent)

asyncio.run(main())
```

## Testing (BDD)

Behaviour-driven scenarios (Gherkin Given/When/Then) live in
`tests/features/*.feature`, bound to step definitions in `tests/test_bdd.py`
via `pytest-bdd`. They assert logical invariants (W+D+L == matches played,
points == 3W+D, standings monotonic in points, name-variant equivalence,
rating/margin ordering) and concrete facts (2019 Brasileirão champion).

```bash
pytest          # 22 scenarios across the 5 capability areas
```

## Specification

See `brazilian-soccer-mcp-guide.md` (mirrored in `TASK.md`).

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
