# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server providing a knowledge-graph-style
query interface over Brazilian soccer data: matches, teams, players,
competitions and statistics, implemented in Python per the specification in
`TASK.md` / `brazilian-soccer-mcp-guide.md`.

## What was implemented

- **`brsoccer/`** — the query engine package:
  - `normalize.py` — team-name canonicalisation across the six datasets'
    naming conventions (`Palmeiras-SP` / `Palmeiras` / `Sport Club Corinthians
    Paulista` / `A.b.c. - RN` / `Red Bull Bragantino` / FIFA's `América FC
    (Minas Gerais)`), with a two-pass `TeamRegistry` that detects ambiguous
    name bases (Santos-SP vs Santos-AP, Botafogo-RJ/PB/SP, ...), resolves
    bare names by count dominance, and keeps accented display names.
  - `dates.py` — multi-format date parsing (ISO, ISO+time, Brazilian
    DD/MM/YYYY) and missing-value sentinels (`NA`, `-`).
  - `models.py` — `Match` / `Player` / computed `TableRow` records.
  - `data.py` — loaders for all six CSVs; cross-file dedupe (the two
    Brasileirão files overlap 2012-2019 and BR-Football overlaps 2014-2023,
    with ±1-day date drift between sources) that collapses leagues on
    `(season, home, away)`, fuzzy-merges cup ties within a day, and grafts
    richer fields (stadium, kickoff, corners/shots/attacks) from dropped
    duplicates. BRF rows dated Jan/Feb are attributed to the previous
    league season (the pandemic-delayed 2020 season ended in Feb 2021).
  - `queries.py` — the query engine: match search, head-to-head, team
    records with home/away splits, computed standings + relegation,
    player search (name/nationality/club/position, FIFA-club ↔ match-team
    join), club overviews, goal averages, biggest wins, best home/away
    records, famous derbies (Fla-Flu, GreNal, Majestoso, Ba-Vi, ...).
  - `formatting.py` — plain-text answers in the spec's answer formats.
  - `mcp_server.py` — MCP server (official `mcp` SDK v2, stdio) exposing
    **16 tools**; bad arguments return friendly guidance text.
- **`server.py`** — stdio entry point (also installed as `brsoccer-mcp`).
- **`tests/`** — BDD Given/When/Then pytest suite: 134 tests covering match,
  team, player, competition and statistics queries; team-name/date/encoding
  data quality; 25 spec sample questions answered end-to-end; real MCP
  stdio client-server integration; and latency guards (<2s simple, <5s
  aggregate per the spec).

Validation highlights: the 2019 Brasileirão table computed from the deduped
data matches the real world exactly (Flamengo 90 pts, 28W 6D 4L — also the
spec's example answer); 2020 relegation (Vasco, Goiás, Coritiba, Botafogo)
matches; every season 2006-2022 collapses to exactly 380 matches.

## Install & run

```bash
python -m venv venv && venv/bin/pip install -e .   # or: pip install -r requirements.txt
venv/bin/python server.py                          # stdio MCP server
```

Configure with any MCP client (Claude Desktop, opencode, ...):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

The datasets are located via `BRSOCCER_DATA_DIR`, `./data/kaggle`, or the
repo layout.

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `find_team` | resolve any team spelling / disambiguate clubs |
| `search_matches` | "Show me all Flamengo vs Fluminense matches", date/season/stage filters, cup finals |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `last_match` | "When did Flamengo last play Corinthians?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?" (computed from results) |
| `relegation` | "Which teams were relegated in 2020?" |
| `competition_info` | coverage of every competition |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `best_records` | "Which team has the best away record?" |
| `derbies` | "Show me all derbies in 2019" |
| `search_players` | "Who is Gabriel Barbosa?", club/position/rating filters |
| `club_overview` | "Find all Brazilian players in the dataset" (per-club breakdown) |
| `data_summary` | dataset coverage overview |

Competition codes: `serie_a`, `serie_b`, `serie_c`, `copa_do_brasil`,
`libertadores` (aliases like `brasileirao` or `copa` work). Note: the FIFA
player snapshot (~FIFA 19) omits some Brazilian clubs (Flamengo, Palmeiras,
Corinthians, São Paulo, Vasco) — those queries return an honest explanation
plus the clubs that are present.

## Tests

```bash
venv/bin/python -m pytest                              # 134 BDD tests
venv/bin/python -m pytest --cov=brsoccer               # ~92% coverage
venv/bin/python -m pytest -m bdd                       # spec scenarios only
venv/bin/python -m pytest -m integration               # MCP stdio end-to-end
venv/bin/python -m pytest -m performance               # latency guards
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
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
