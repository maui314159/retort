# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server providing a knowledge graph interface for Brazilian soccer data. Enables natural language queries about players, teams, matches, and competitions using Kaggle datasets.

## Quick Start

```bash
npm install
npm run build
npm start        # starts MCP server on stdio
npm test         # runs BDD test suite
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_matches` | Find matches by team, opponent, competition, season, or date range |
| `get_team_stats` | Win/loss/draw records and goals for a team (optionally filtered by season/competition/home-only) |
| `search_players` | Search FIFA player data by name, nationality, club, position, or rating |
| `get_competition_standings` | Calculated league table from match results for a given season |
| `get_head_to_head` | Head-to-head comparison between two teams |
| `get_statistics` | Aggregate stats: average goals, home/away win rates, biggest victories |

## Data Sources

Kaggle datasets (freely available with attribution) in `data/kaggle/`:

| File | Records | Source | License |
|------|---------|--------|---------|
| `Brasileirao_Matches.csv` | 4,180 matches | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 matches | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 matches | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 matches | [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 matches | [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 players | [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

## Architecture

- **`src/types.ts`** — Shared type definitions (MatchRecord, PlayerRecord, StandingEntry, etc.)
- **`src/loader.ts`** — CSV loading and team name normalization. Strips state suffixes (e.g., "Palmeiras-SP" → "Palmeiras"), resolves known aliases, and parses multiple date formats.
- **`src/data.ts`** — Unified data access layer implementing all five query categories with formatting helpers.
- **`src/index.ts`** — MCP server entry point registering six tools via the MCP SDK stdio transport.
- **`tests/data.test.ts`** — 47 BDD-style (Given/When/Then) tests covering all query categories, data coverage, and cross-file queries.

## Team Name Normalization

The datasets use different naming conventions for the same clubs. The loader normalizes names by:
1. Stripping state suffixes (`-SP`, ` - RJ`)
2. Removing parenthetical annotations
3. Resolving known aliases (e.g., "sao paulo" → "São Paulo", "botafogo-rj" → "Botafogo")

## Testing

BDD-style tests with Given/When/Then structure cover:
- Match queries (team, opponent, competition, season, date range, limit)
- Team statistics (overall, season-filtered, home-only, competition-filtered, win rate)
- Player queries (name, nationality, club, position, rating, sort order)
- Competition standings (points calculation, goal difference, champion verification)
- Statistical analysis (aggregate stats, home advantage, biggest victories)
- Head-to-head comparison (wins/draws, goals, recent matches, consistency)
- Data coverage (all 6 CSV files loaded, extended stats)
- Cross-file queries (player + match data combined)
