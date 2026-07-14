# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a queryable interface to Brazilian soccer data — matches, teams, players, competitions, and statistics — using pre-downloaded Kaggle datasets.

## Quick Start

```bash
# Install (editable, with dev dependencies for testing)
pip install -e ".[dev]"

# Run the MCP server (stdio transport)
python server.py

# Run BDD tests
pytest tests/ -v
```

## Architecture

| File | Purpose |
|------|---------|
| `server.py` | MCP server exposing 9 tools via FastMCP |
| `data_loader.py` | CSV loading, team-name normalisation, query functions |
| `data/kaggle/` | Six Kaggle CSV datasets (see below) |
| `tests/` | BDD (pytest-bdd) test suite with Gherkin feature files |

## MCP Tools

| Tool | Description |
|------|-------------|
| `query_matches` | Search matches by team, opponent, competition, season, date range |
| `team_statistics` | Win/draw/loss record and goals for a team |
| `head_to_head` | Compare two teams head-to-head across all match data |
| `query_players` | Search FIFA player data by name, nationality, club, position, rating |
| `competition_standings` | Calculate standings (3-1-0 points) for a competition/season |
| `match_statistics` | Aggregate stats: avg goals, home win rate, biggest wins |
| `available_competitions` | List all competition names in the dataset |
| `available_seasons` | List all seasons, optionally filtered by competition |
| `available_teams` | List all team names, optionally filtered by competition |

## Data Sources

| File | Records | License |
|------|---------|---------|
| `Brasileirao_Matches.csv` | ~4,180 matches | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | ~1,337 matches | CC BY 4.0 |
| `Libertadores_Matches.csv` | ~1,255 matches | CC BY 4.0 |
| `BR-Football-Dataset.csv` | ~10,296 matches (extended stats) | CC0 |
| `novo_campeonato_brasileiro.csv` | ~6,886 matches (2003–2019) | CC BY 4.0 |
| `fifa_data.csv` | ~18,207 players | Apache 2.0 |

## Design Decisions

- **Team name normalisation**: Datasets use inconsistent naming (e.g., "Palmeiras-SP" vs "Palmeiras"). The `normalize_team()` function strips state suffixes and lowercases for matching while preserving the canonical title-case form for display.
- **Date handling**: Multiple formats (ISO `2023-09-24`, Brazilian `29/03/2003`, datetime with time) are parsed per-dataset at load time.
- **Lazy matching**: Team and competition filters use substring matching (case-insensitive) to handle the wide variation in naming across sources.
- **Data loading**: All CSVs are loaded once at module import time into module-level DataFrames. Query functions return plain dicts/lists, never pandas objects.

## Testing

14 BDD scenarios across 7 feature files covering all five required capability categories plus data quality and coverage:

```
tests/match_queries.feature       — Match search, filtering by team/season/competition
tests/team_queries.feature        — Team statistics, head-to-head comparison
tests/player_queries.feature      — Player search by nationality and club
tests/competition_queries.feature — Standings calculation
tests/statistical_analysis.feature — Aggregate match statistics
tests/team_normalisation.feature  — Team name normalisation (Scenario Outline)
tests/data_coverage.feature       — All CSV files loadable and queryable
```
