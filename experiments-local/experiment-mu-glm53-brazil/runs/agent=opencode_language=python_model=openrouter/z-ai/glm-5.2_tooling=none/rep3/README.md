# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that exposes a knowledge-graph-style
query interface over six Kaggle Brazilian-soccer datasets, enabling an LLM
to answer natural-language questions about players, teams, matches, and
competitions.

Implements the specification in [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Stack

- **Language:** Python 3.12
- **MCP SDK:** `mcp` v1 (`FastMCP`), pinned via `mcp<2`
- **Data:** stdlib `csv` only — no pandas/numpy dependency
- **Tests:** `pytest` with BDD (Given/When/Then) scenarios

## Project layout

```
normalizer.py          # team-name canonicalization (suffix/prefix/alias handling)
data_loader.py         # loads & unifies all 6 CSVs into SoccerData
analysis.py            # pure-Python query/analysis engine
server.py              # FastMCP tool surface (13 tools)
conftest.py            # shared session-scoped SoccerData fixture
tests/                 # BDD test suites (52 scenarios)
  test_normalizer.py
  test_data_loader.py
  test_analysis.py
  test_server.py
data/kaggle/           # the 6 source CSVs (pre-downloaded, see README data section)
```

## Datasets loaded

| File | Records | Role |
|------|--------:|------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Serie A (2012–2022) |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil (2012–2021) |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores (2013–2023) |
| `BR-Football-Dataset.csv` | 10,296 | Serie A/B/C + Cup extended stats |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão (2003–2019) |
| `fifa_data.csv` | 18,207 | FIFA player database |

Total: **23,954 unified matches** + **18,207 players**, indexed by team and season.

## MCP tools (13)

**Match / Team**
- `search_matches_tool` — filter by team, opponent, competition, season, date range
- `head_to_head_tool` — win/draw/loss + match list between two teams
- `team_stats_tool` — W/D/L, goals, home/away split (optionally per season)

**Competition**
- `standings_tool` — computed league table (3 pts/win)
- `champion_tool` — top of standings
- `relegated_teams_tool` — bottom-n teams

**Statistics**
- `biggest_wins_tool` — ranked by goal margin
- `average_goals_tool` — avg goals/match + home/draw/away rates
- `best_home_record_tool` — teams ranked by home win rate
- `derbies_tool` — traditional Brazilian rivalry matches

**Players**
- `search_players_tool` — by name/nationality/club/position/rating
- `top_brazilian_players_tool`
- `players_at_club_tool`

## Running

```bash
source venv/bin/activate
pip install "mcp<2"          # if not already installed
python server.py             # stdio MCP server
```

Point any MCP client (e.g. Claude Desktop) at `python /path/to/server.py`.

## Testing

```bash
source venv/bin/activate
python -m pytest -q          # 52 BDD scenarios, ~1s
```

Tests follow the BDD GWT structure mandated by the spec, e.g.:

```python
# Scenario: Find matches between two teams
def test_flamengo_vs_fluminense(self, sd):
    # Given the match data is loaded
    # When I search for matches between Flamengo and Fluminense
    results = search_matches(sd, team="Flamengo", opponent="Fluminense", limit=200)
    # Then I should receive a list of matches
    assert len(results) > 0
```

## Data-quality handling

- **Team names:** suffix stripping (`-SP`, ` - RJ`, `-EQU`), leading legal-prefix
  stripping (`Sociedade Esportiva `, `Sport Club `), trailing legal-suffix
  stripping (` Sport Club`, ` S/A`), parenthetical removal, accent-preserving
  display names with accent-folded equality keys. See `normalizer.py`.
- **Dates:** ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`), and
  Brazilian (`29/03/2003`) formats all parsed to ISO. `NA` sentinels → `None`.
- **Goals:** int (`2`), float-string (`1.0`), and empty all coerced safely.
- **Encoding:** all files read as UTF-8 (Grêmio, Avaí, São Paulo preserved).

## Verification highlights

- 2019 Brasileirão champion correctly computed as **Flamengo** (90 pts).
- Fla-Flu head-to-head: Flamengo 31 wins in the unified dataset.
- Biggest win margin in dataset: 8 goals.
- Average goals/match (Brasileirão): **2.51**, with home win rate > away
  win rate (home advantage confirmed).

## Data sources & licenses

See [README data section](#datasets-loaded) above and the source attributions
in the original Kaggle links:
- [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) (CC BY 4.0)
- [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) (CC0)
- [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) (CC BY 4.0)
- [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) (Apache 2.0)
