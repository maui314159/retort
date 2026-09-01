# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a query interface over
Brazilian soccer datasets, enabling natural-language questions about matches,
teams, players and competitions.

## What was implemented

A pure-Python MCP server (no Neo4j/runtime deps beyond the `mcp` SDK) that
loads all six Kaggle CSVs from `data/kaggle/`, normalizes team names and
dates, and exposes 15 query tools over stdio JSON-RPC.

### Package layout

```
brazilian_soccer_mcp/
  __init__.py        # package entry point
  data_loader.py     # loads & normalizes all 6 CSVs; TeamResolver disambiguates
                     # same-name clubs from different states (Atletico-MG vs -PR)
  queries.py         # SoccerQueryEngine: matches / teams / players / competitions / stats
  mcp_server.py      # MCPServer (stdio) registering 15 tools
tests/
  conftest.py        # session-scoped engine fixture
  test_matches.py    # BDD Given/When/Then match-query scenarios
  test_teams.py      # team stats, venue splits, comparison
  test_players.py    # FIFA player search, nationality/club filters
  test_competitions.py # standings, champion, relegation, metadata
  test_statistics.py # avg goals, biggest wins, away record, top scorers
  test_mcp.py        # tool discovery, dispatch, data-coverage contract
pytest.ini
setup.py
```

### Datasets loaded (all from `data/kaggle/`)

| File | Records | Role |
|------|---------|------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Serie A (2012-2022) |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil (2012-2021) |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores (2013-2022) |
| `BR-Football-Dataset.csv` | 10,296 | extended match statistics |
| `novo_campeonato_brasileiro.csv` | 6,886 | historical Brasileirão (2003-2019) |
| `fifa_data.csv` | 18,207 | FIFA player database |

Total: ~23,954 matches + 18,207 players, loaded in < 1 s.

### Key normalization handled

- **Team name variations**: a `TeamResolver` builds a canonical key per club.
  State suffixes (`-SP`, `-MG`) are stripped when the bare name is unique
  (so `Palmeiras-SP` == `Palmeiras`) but **retained** to disambiguate
  same-name clubs (`Atletico-MG` ≠ `Atletico-PR`).
- **Date formats**: ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) are all parsed.
- **UTF-8**: accents (São Paulo, Grêmio, Avaí) preserved; matching is
  accent-insensitive.

## MCP tools exposed

`find_matches`, `head_to_head`, `team_stats`, `compare_teams`, `find_players`,
`top_players_for_club`, `brazilian_players`, `standings`, `competition_info`,
`champion`, `relegated_teams`, `average_goals`, `biggest_wins`,
`best_away_record`, `top_scoring_teams`.

## Running

```bash
# install deps (mcp SDK) into the provided venv
source venv/bin/activate
pip install -e .

# run the MCP server over stdio
python -m brazilian_soccer_mcp.mcp_server
```

## Testing

BDD (Given/When/Then) scenarios with pytest:

```bash
source venv/bin/activate
python -m pytest
```

All 31 scenarios pass. They cover the success criteria from the spec:
match/team/player/competition/statistical queries, team-name normalization,
state disambiguation, standings calculation, and MCP tool discovery/dispatch.

## Data sources & licenses

See `README.md` (top of file) and `TASK.md` for the Kaggle dataset attributions
(CC BY 4.0, CC0, Apache 2.0). This implementation is for demo/non-commercial
use as stated in the specification.
