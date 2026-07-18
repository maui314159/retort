# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that provides a knowledge graph
interface for Brazilian soccer data. It loads six Kaggle datasets (matches,
players, teams, competitions) into an in-memory graph and exposes 13
LLM-callable tools for querying matches, teams, players, competitions, and
statistics.

## What was implemented

### Architecture

```
CSV files → data_loader → Match/Player records → KnowledgeGraph → QueryEngine → MCP tools
                                                              (indexes)        (server.py)
```

The server loads all datasets once at startup (~4 s) into an in-memory
knowledge graph with pre-built indexes, then serves every query from memory in
sub-second time.

### Package structure

| File | Purpose |
|------|---------|
| `brazilian_soccer_mcp/models.py` | Domain dataclasses: `Match`, `Player`, `Team`, `Competition`, `Node`, `Edge` |
| `brazilian_soccer_mcp/normalize.py` | Team-name normalizer — handles state suffixes, accents, collision disambiguation |
| `brazilian_soccer_mcp/data_loader.py` | Loads 6 CSV files into typed records; cross-source deduplication |
| `brazilian_soccer_mcp/knowledge_graph.py` | In-memory graph with adjacency lists and lookup indexes |
| `brazilian_soccer_mcp/query_engine.py` | 13 query methods returning formatted answer strings |
| `brazilian_soccer_mcp/server.py` | FastMCP server wrapping the query engine as LLM-callable tools |

### MCP Tools (13)

**Match Queries:** `search_matches`, `head_to_head`
**Team Queries:** `team_statistics`, `compare_teams`, `team_competitions`
**Player Queries:** `search_players`, `top_players_at_club`, `top_brazilian_players`
**Competition Queries:** `standings`, `competition_info`
**Statistical Analysis:** `average_goals`, `biggest_wins`, `best_records`

### Key engineering decisions

**Team name normalization.** The datasets spell clubs in dozens of incompatible
ways: with/without state suffixes ("Palmeiras-SP" vs "Palmeiras"), with/without
accents ("São Paulo" vs "Sao Paulo"), and with full official names
("Atlético Mineiro"). The normalizer uses a two-layer strategy:
1. Manual alias table for collision-prone clubs where different clubs share a
   base name (Atlético-MG vs Atletico-PR vs Atlético-GO must stay distinct).
2. Automatic collision resolution: if a base name appears with multiple state
   suffixes, the suffix is kept as a disambiguator; otherwise it's dropped.

**Cross-source deduplication.** BR-Football-Dataset.csv overlaps
Brasileirao_Matches.csv (Serie A 2014-2022) and Brazilian_Cup_Matches.csv (Copa
do Brasil 2014-2021). Keeping both would double-count matches and corrupt
standings. The loader tracks (competition, season) pairs from primary sources
and skips overlapping seasons in BR-Football. BR-Football still contributes
its unique value: full Serie B/C coverage, extended stats (corners/shots), and
seasons beyond the primary files (e.g. Serie A 2023).

**Historical Brasileirão.** novo_campeonato_brasileiro.csv covers 2003-2019,
but 2012-2019 overlap with Brasileirao_Matches.csv. Only seasons < 2012 are
kept, giving a single clean Brasileirão Serie A series spanning 2003-2022.

## Data sources

All datasets are in `data/kaggle/` and are loaded at startup:

| File | Records | Coverage |
|------|---------|----------|
| `Brasileirao_Matches.csv` | 4,180 matches | Brasileirão Serie A 2012-2022 |
| `novo_campeonato_brasileiro.csv` | 6,886 matches (2003-2011 kept) | Brasileirão Serie A 2003-2011 |
| `Brazilian_Cup_Matches.csv` | 1,337 matches | Copa do Brasil 2012-2021 |
| `Libertadores_Matches.csv` | 1,255 matches | Copa Libertadores 2013-2022 |
| `BR-Football-Dataset.csv` | 10,296 matches (deduped) | Serie A/B/C + Copa do Brasil, extended stats |
| `fifa_data.csv` | 18,207 players | FIFA player database |

**Licenses:** CC BY 4.0, CC0 Public Domain, Apache 2.0 (see source links below).

## Installation

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Running the server

```bash
# via module (stdio transport — standard for MCP)
python -m brazilian_soccer_mcp

# via script
python brazilian_soccer_mcp/server.py

# via entry point
brazilian-soccer-mcp
```

### Claude Desktop config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp"]
    }
  }
}
```

## Example queries

```
"Show me all Flamengo vs Fluminense matches"
  → head_to_head(team_a="Flamengo", team_b="Fluminense")

"Who won the 2019 Brasileirão?"
  → standings(competition="Brasileirão", season=2019)
  → Flamengo - 90 pts (28W, 6D, 4L) - Champion

"What is Corinthians' home record in 2022?"
  → team_statistics(team="Corinthians", season=2022, competition="Brasileirão", venue="home")

"Who are the highest-rated Brazilian players?"
  → top_brazilian_players(limit=10)
  → Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain

"What's the average goals per match in the Brasileirão?"
  → average_goals(competition="Brasileirão")
  → Average goals per match: 2.57
```

## Testing

Tests use BDD (Behavior-Driven Development) with `pytest-bdd` plus direct
unit tests:

```bash
python -m pytest tests/ -v
```

### BDD features

```
tests/features/
├── match_queries.feature         # Find matches by team, competition, season
├── team_queries.feature          # Team statistics, comparison, competitions
├── player_queries.feature        # Search players by name, nationality, club
├── competition_queries.feature    # Standings, competition info
└── statistical_analysis.feature  # Avg goals, biggest wins, best records
```

### Test coverage (59 tests, all passing)

- **BDD scenarios** (15): Given/When/Then steps matching the spec's Gherkin
  examples
- **Normalizer unit tests** (7): suffix stripping, accent folding, collision
  disambiguation
- **Data loader tests** (8): record counts, date parsing, cross-source dedup
- **Knowledge graph tests** (7): node/edge counts, index completeness
- **Query engine tests** (13): every query method with real data
- **MCP server tests** (2): tool registry, tool callability
- **Performance tests** (2): simple lookup < 2s, aggregate < 5s (per spec)

## Data sources (Kaggle)

- [Brasileirão matches](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) (CC BY 4.0)
- [Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) (CC0)
- [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) (CC BY 4.0)
- [FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) (Apache 2.0)

## License

MIT (code). Data licenses remain with their respective sources (see above).
