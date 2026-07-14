# Brazilian Soccer MCP Server

MCP (Model Context Protocol) server providing query tools for Brazilian soccer data. Supports natural language queries about matches, teams, players, competitions, and statistics.

## Architecture

```
data_loader.py   → CSV loading, team name normalization, date parsing
query_engine.py  → Query functions: match, team, player, competition, stats
server.py        → FastMCP server exposing 13 tools via MCP protocol
test_server.py   → BDD GWT PyTest tests (42 scenarios)
```

## Quickstart

```bash
# Install dependencies
pip install pandas mcp pytest

# Run tests
python -m pytest test_server.py -v

# Run the MCP server (stdio transport)
python server.py
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `find_matches` | Search matches by team, competition, season, date range |
| `team_stats` | Wins, losses, draws, goals, home/away records |
| `head_to_head` | Compare two teams head-to-head |
| `best_home_record` | Teams with best home record |
| `best_away_record` | Teams with best away record |
| `find_players` | Search FIFA player database |
| `brazilian_players_summary` | Brazilian players overview |
| `competition_standings` | Calculate league tables |
| `competitions_for_team` | List competitions a team played in |
| `average_goals` | Goals/match, home/away win rates |
| `biggest_wins` | Largest goal differences |
| `season_comparison` | Compare two seasons side-by-side |
| `most_goals_team` | Top scoring teams |

## Data Sources

Kaggle datasets (freely available with attribution):

### Match Data
- **Brasileirao_Matches.csv** (4,180 matches): Serie A 2012-2022 — [CC BY 4.0](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
- **Brazilian_Cup_Matches.csv** (1,337 matches): Copa do Brasil — [CC BY 4.0](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
- **Libertadores_Matches.csv** (1,255 matches): Copa Libertadores — [CC BY 4.0](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
- **BR-Football-Dataset.csv** (10,296 matches): Extended match stats — [CC0 Public Domain](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)
- **novo_campeonato_brasileiro.csv** (6,886 matches): Historical Brasileirao 2003-2019 — [CC BY 4.0](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)

### Player Data
- **fifa_data.csv** (18,207 players): FIFA player ratings — [Apache 2.0](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)

### Unified Dataset
All 5 match sources are merged into a single dataset of **23,953 matches** spanning 2003-2023 across Brasileirao, Copa do Brasil, and Libertadores.

## Data Handling

- **Team names**: Normalized to strip state suffixes (`Palmeiras-SP` → `palmeiras`), accents (`São Paulo` → `sao-paulo`), and handle common variations (`Vasco da Gama` → `vasco`)
- **Dates**: Parse ISO (`2023-09-24`), Brazilian (`29/03/2003`), and datetime (`2012-05-19 18:30:00`) formats
- **Encoding**: UTF-8 with replacement for malformed characters

## Testing

42 BDD (Behavior-Driven Development) tests using Given-When-Then structure:

- **TestDataLoading** (5 tests): All 6 CSV files load with expected structure
- **TestTeamNormalization** (3 tests): State suffixes, accents, common variations
- **TestMatchQueries** (6 tests): By team, head-to-head, season, competition, date range, no results
- **TestTeamQueries** (5 tests): Stats, by season, nonexistent, head-to-head valid/invalid
- **TestPlayerQueries** (7 tests): Nationality, name, club, position, rating, summary, no results
- **TestCompetitionQueries** (3 tests): Standings, historical, team competitions
- **TestStatisticalAnalysis** (6 tests): Average goals, biggest wins, season compare, top scorers, home/away records
- **TestIntegrationSmoke** (7 tests): End-to-end natural language question scenarios