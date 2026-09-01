# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language-backed
tool queries about Brazilian soccer — matches, teams, players, competitions
and statistics — over the Kaggle datasets in `data/kaggle/`.

Implemented per `brazilian-soccer-mcp-guide.md` / `TASK.md`.

## What was done

- **Data layer** (`soccer/loader.py`): loads all six CSV datasets into a
  unified in-memory match model plus the FIFA player database.
  - Team names are normalized across naming conventions
    (`soccer/normalize.py`): state suffixes ("Palmeiras-SP"),
    legal names ("Sport Club Corinthians Paulista"), accents and
    cross-dataset aliases ("Vasco" ↔ "Vasco da Gama") all resolve to one
    canonical key.
  - Date formats handled: ISO, ISO+time and Brazilian `DD/MM/YYYY`.
  - Overlapping fixtures between the aggregate and detailed datasets are
    de-duplicated (keyed on season/competition/teams, since source dates
    are timezone-shifted); detailed corner/shot/attack statistics and
    venue info are merged into the surviving record.
- **Query layer** (`soccer/queries.py`): match search (team, opponent,
  competition, season, date range, stage incl. "final"), head-to-head
  records, team stats with home/away splits, standings computed from
  match results, relegation zone, player search (name / nationality /
  club / position / rating), Brazilian-players-by-club summary, biggest
  wins, goals & home-advantage statistics, season comparison, and derby
  finding (Fla-Flu, Grenal, Choque-Rei, ...).
- **MCP server** (`soccer/server.py`, entrypoint `server.py`): 16 tools
  exposed over stdio via the official `mcp` Python SDK (v2, `MCPServer`).
- **Tests** (`tests/`): 64 BDD/GWT-style pytest scenarios (Gherkin
  scenarios expressed as docstrings) covering normalization, matches,
  teams, players, competitions, statistics, and the MCP server layer
  itself (exercised through the real `call_tool` API).

## Running

```bash
# use the existing virtualenv
source venv/bin/activate

# run the MCP server over stdio
python server.py

# run the test suite
python -m pytest -q
```

To connect from an MCP client, register the server as a stdio process:

```json
{ "command": "venv/bin/python", "args": ["server.py"] }
```

## Example tool calls

| Tool | Arguments | Result |
|------|-----------|--------|
| `head_to_head` | Flamengo vs Fluminense | 44 matches, win/draw/loss split |
| `standings` | season 2019 | Flamengo champion (90 pts) |
| `find_matches` | competition "Copa do Brasil", stage "final" | all 14 finals in the data |
| `search_players` | nationality "Brazil" | top-rated Brazilian players |
| `team_stats` | Corinthians, season 2022, venue home | 28 M / 18 W / 8 D / 2 L (all comps) |

## Data sources

Kaggle datasets (freely available with attribution), shipped in
`data/kaggle/` — see `brazilian-soccer-mcp-guide.md` for column-level
descriptions and licenses:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro (CC BY 4.0)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches (CC0)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 (CC BY 4.0)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data (Apache 2.0)

Known data caveats (handled or accepted):

- The FIFA dataset (FIFA 19) licenses only some Brazilian clubs —
  Flamengo, Palmeiras, Corinthians and São Paulo are absent; Grêmio,
  Santos, Fluminense etc. are present.
- A few genuine same-key club collisions remain (e.g. "América-MG" vs
  "América-RN", "Nacional-AM" vs Nacional URU) because state suffixes
  are stripped for cross-file matching.
