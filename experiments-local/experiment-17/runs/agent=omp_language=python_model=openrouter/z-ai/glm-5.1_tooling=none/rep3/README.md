# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a knowledge-graph interface for Brazilian soccer data. Enables natural-language queries about players, teams, matches, and competitions using Kaggle datasets.

## Quick Start

```bash
# Install dependencies
pip install mcp[cli] pandas

# Run the server (stdio transport, for MCP clients)
python server.py

# Or use the MCP dev tool for inspection
mcp dev server.py
```

## Architecture

| File | Purpose |
|------|---------|
| `server.py` | MCP server with 12 tools across 5 categories |
| `data_loader.py` | Loads & normalizes all 6 CSV datasets into pandas DataFrames |
| `tests/` | BDD (pytest-bdd) test suite |

## Data Sources

All data is in `data/kaggle/`:

| File | Records | Source | License |
|------|---------|--------|---------|
| `Brasileirao_Matches.csv` | 4,180 matches | [Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 matches | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 matches | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 matches | [Kaggle](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 matches | [Kaggle](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 players | [Kaggle](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

## MCP Tools

### 1. Match Queries
- **`search_matches`** — Search by team, opponent, competition, season, date range
- **`head_to_head`** — Head-to-head record between two teams

### 2. Team Queries
- **`team_statistics`** — Win/draw/loss record, goals for/against, home/away split
- **`top_teams_by_goals`** — Rank teams by total goals scored

### 3. Player Queries
- **`search_players`** — Search FIFA data by name, nationality, club, position, rating
- **`players_at_club`** — List players at a given club

### 4. Competition Queries
- **`competition_standings`** — Calculate league standings from match results
- **`list_competitions`** — List all competitions in the dataset
- **`list_seasons`** — List available seasons (optionally filtered by competition)

### 5. Statistical Analysis
- **`avg_goals_per_match`** — Average goals, home/away win rates
- **`biggest_wins`** — Largest victories by goal difference
- **`home_vs_away`** — Compare home vs away performance

## Key Design Decisions

### Team Name Normalization
Different datasets use different conventions:
- State suffix: `"Palmeiras-SP"`, `"Flamengo-RJ"`
- No suffix: `"Palmeiras"`, `"Flamengo"`
- Parenthetical notes: `"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"`

All team names are normalized by stripping state suffixes (`-XX`) and parenthetical annotations during data loading.

### Date Format Handling
Datasets use mixed formats (ISO `YYYY-MM-DD`, Brazilian `DD/MM/YYYY`, with timestamps). The loader tries ISO first, then falls back to day-first parsing.

## Testing

BDD tests using pytest-bdd with Gherkin feature files:

```bash
pip install pytest pytest-bdd pytest-asyncio
python -m pytest tests/ -v
```

19 test scenarios covering all 5 tool categories: match queries, team queries, player queries, competition queries, and statistical analysis.
