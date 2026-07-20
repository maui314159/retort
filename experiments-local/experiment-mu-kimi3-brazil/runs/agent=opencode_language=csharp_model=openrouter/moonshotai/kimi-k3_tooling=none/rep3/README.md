# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, implemented in C# / .NET 10, that exposes a
knowledge-graph interface over six Kaggle datasets of Brazilian soccer. It answers
natural-language questions about matches, teams, players, competitions and statistics
via 13 MCP tools, speaking JSON-RPC 2.0 over stdio with zero external dependencies.

## What was implemented

- **Unified, deduplicated dataset** from all six CSVs (`src/BrazilianSoccerMcp/Data/`):
  - Quote-aware CSV parser (handles embedded commas, doubled quotes, UTF-8 BOMs, CRLF).
  - Multi-format date parsing (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`).
  - Team-name normalization unifying the different file conventions:
    `Palmeiras-SP`, `América - MG`, `Audax SP`, `Sport Club Corinthians Paulista`,
    `Athletico Paranaense`, `Atlético Mineiro`, ... all map to stable canonical keys,
    while genuinely different clubs sharing a base name stay distinct
    (`atletico mg` vs `atletico go`, `Botafogo-RJ` vs `Botafogo PB`).
  - `NA` scores (postponed matches) are kept but excluded from all statistics.
  - Because the five match files overlap (the 2019 season appears in three of them),
    each (competition, season) is taken from exactly one authoritative source.
    Result: Brasileirão Série A 2003-2023, Copa do Brasil 2012-2023,
    Copa Libertadores 2013-2022, Série B/C 2014-2023 — every file contributes.
- **In-memory knowledge graph** (`Graph/KnowledgeGraph.cs`): team, player, competition,
  season and match nodes with adjacency indexes (team -> matches -> opponents,
  club -> players), fuzzy team resolution with ambiguity notes, and graph statistics.
- **Query services** (`Services/`): match search, head-to-head, team records,
  standings computed from results (3/1/0 points), biggest wins, competition
  aggregates, and player search/club squads/top-rated lists.
- **MCP server** (`Mcp/McpServer.cs`): newline-delimited JSON-RPC 2.0 over stdio
  implementing `initialize`, `ping`, `tools/list`, `tools/call` (plus empty
  `resources/list` / `prompts/list`). Only protocol messages touch stdout.
- **94 BDD-structured xUnit tests** (`tests/`, Given/When/Then naming) covering all
  five required query categories against the real data, e.g. Flamengo's 2019 title
  with exactly 90 pts (28W 6D 4L) and Cruzeiro's 100-point 2003 campaign.

## MCP tools

| Tool | Answers |
|---|---|
| `find_matches` | matches by team/opponent/competition/season/dates/venue/round |
| `head_to_head` | all matches between two teams + win/draw tally |
| `team_statistics` | W/D/L, goals for/against, win rate (season/competition/venue) |
| `competition_standings` | league table computed from results (incl. relegation zone) |
| `competition_stats` | avg goals/match, home/draw/away win rates |
| `biggest_wins` | largest victory margins |
| `search_players` | FIFA players by name/nationality/club/position/min rating |
| `club_players` | top-rated squad of a club |
| `top_players` | highest-rated players (e.g. top Brazilians) |
| `brazilian_players_summary` | count, top rated, per-Brazilian-club breakdown |
| `list_competitions` | competitions with season coverage and match counts |
| `list_teams` | team directory with match counts |
| `graph_stats` | knowledge-graph node/edge counts and per-file contributions |

## Build, test, run

```bash
dotnet build BrazilianSoccerMcp.slnx          # build
dotnet test  BrazilianSoccerMcp.slnx          # 94 tests
dotnet run --project src/BrazilianSoccerMcp   # serve MCP over stdio
```

The server locates `data/kaggle` automatically (walks up from the working
directory), or via `--data-dir <path>` / `BRAZILIAN_SOCCER_DATA_DIR`.

### Claude Desktop configuration

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "/path/to/src/BrazilianSoccerMcp"]
    }
  }
}
```

## Sample answers

```
2019 Brasileirão Série A standings (computed from 380 matches):
 1. Flamengo-RJ - 90 pts (28W, 6D, 4L, GF 86, GA 37)
 2. Santos-SP - 74 pts (22W, 8D, 8L, GF 60, GA 33)
 3. Palmeiras-SP - 74 pts (21W, 11D, 6L, GF 61, GA 32)
```

```
Corinthians record (home matches, 2022, Brasileirão Série A):
Matches: 15 | Wins: 10, Draws: 4, Losses: 1
Goals For: 21, Goals Against: 7 | Goal Difference: +14
Win rate: 66.7%
```

```
Brazilian players in FIFA dataset: 827
Top-rated:
1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain
...
```

## Specification

`TASK.md` (identical to `brazilian-soccer-mcp-guide.md`).

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
