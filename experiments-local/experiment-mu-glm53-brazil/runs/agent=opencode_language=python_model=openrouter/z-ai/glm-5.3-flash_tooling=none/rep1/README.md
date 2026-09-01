# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Server

An MCP (Model Context Protocol) server exposing a knowledge-graph style
interface over the six Kaggle datasets in `data/kaggle/` (5 match files,
18k FIFA players). Team names, dates, and competition labels are normalized
across files ("Palmeiras-SP" = "Palmeiras", "29/03/2003" = "2003-03-29",
"serie a" = "Brasileirão"), and overlapping match records between sources
are de-duplicated so season standings compute cleanly.

### Run

```bash
python -m pip install -r requirements.txt
python -m brazilian_soccer_mcp          # stdio MCP server
```

Data directory resolution: `BRAZILIAN_SOCCER_DATA_DIR` env var, else
`<repo>/data/kaggle`.

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team/opponent (either side), competition, season, date range, round/stage |
| `get_team_stats` | W/D/L record, goals for/against, win rate; filter by competition, season, venue |
| `head_to_head` | Head-to-head W/D/L between two teams + recent meetings + derby name |
| `search_players` | FIFA players by name, nationality, club, position/category, overall range |
| `get_standings` | League table computed from match results (champion, relegation zone) |
| `get_competition_stats` | Avg goals/match, home/away/draw rates, top scoring teams, biggest wins |
| `get_best_records` | Best home/away win rates for a competition/season |
| `search_derbies` | Classic rivalry matches (Fla-Flu, Gre-Nal, Dérbi Paulista, ...) |
| `get_team_competitions` | Competitions and seasons a team appears in across all files |
| `get_club_overview` | Cross-file: match record + FIFA squad for a club |
| `get_season_summary` / `compare_seasons` | Season-wide aggregates and side-by-side comparison |
| `list_teams` / `list_competitions` | Discovery of team names and competition/season coverage |

### Programmatic use

```python
from brazilian_soccer_mcp import Dataset, QueryEngine

engine = QueryEngine(Dataset())
engine.get_standings("brasileirao", 2019)["standings"][0]
# {'position': 1, 'team': 'Flamengo', 'points': 90, ...}
```

### Tests

```bash
python -m pytest tests/
```

125 tests cover normalization, loading/dedup, every query capability, and an
end-to-end MCP stdio client round-trip against `python -m brazilian_soccer_mcp`.

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
