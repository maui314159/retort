# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that turns the
provided Kaggle datasets into a knowledge-graph-style query interface over
Brazilian soccer: matches, teams, players, competitions and statistics. An LLM
client connects over stdio and calls the tools to answer natural-language
questions such as *"Who won the 2019 Brasileirão?"* or *"Compare Palmeiras and
Santos head-to-head."*

Implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in `TASK.md`).

## What was built

- **C# / .NET 10** solution (`BrazilianSoccerMcp.slnx`) with three projects:
  - `src/BrazilianSoccer.Core` — data loading, name normalization, the query
    engine and answer formatting. No MCP dependency, fully unit-testable.
  - `src/BrazilianSoccer.Server` — the MCP server (`ModelContextProtocol` SDK)
    exposing the query engine as tools over stdio.
  - `tests/BrazilianSoccer.Tests` — xUnit BDD (Given/When/Then) tests.
- All six CSV files are loaded into one unified `Match` / `Player` model
  (~24k raw match rows → deduplicated, 18,207 players).

### Data handling highlights

- **Team-name normalization** (`NameNormalizer`): folds accents, strips state
  (`-SP`) and country (`(URU)`) suffixes, collapses verbose legal names
  ("Sport Club Corinthians Paulista" → Corinthians) and spelling variants
  ("Vasco" / "Vasco da Gama", "Athletico Paranaense" / "Atlético-PR"). Clubs
  that share a base name are kept distinct **by state** (Atlético-MG vs
  Athletico-PR vs Atlético-GO, Botafogo-RJ vs Botafogo-SP).
- **Cross-source deduplication** (`DataLoader`): Série A appears in three of the
  files; identical fixtures are collapsed (round-robin fixture key, tolerant of
  the ±1-day date drift between sources) and their extended stats merged. This
  is what makes calculated standings correct — e.g. the 2019 Brasileirão comes
  out exactly as the real table: **Flamengo champion, 90 pts (28W 6D 4L)**.
- **Multiple date formats** parsed: ISO (`2023-09-24`), Brazilian
  (`29/03/2003`), with time, and `yyyy.MM.dd`.
- **UTF-8** throughout; Portuguese accents preserved in display names.

## MCP tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team / opponent / competition / season / date range |
| `head_to_head` | Wins, draws, goals and match list between two teams |
| `team_record` | W/D/L and goals for a team (by season, competition, home/away) |
| `find_players` | FIFA players by name, nationality, club, position (rating-sorted) |
| `league_standings` | League table calculated from match results (3pts win / 1 draw) |
| `goal_statistics` | Average goals per match and home-win rate |
| `biggest_wins` | Largest-margin victories |
| `best_records` | Teams ranked by home or away win rate |
| `team_competitions` | Competitions a team has appeared in, with counts |

## Build and test

```bash
dotnet build          # builds all three projects
dotnet test           # runs the BDD test suite (47 tests)
```

## Run the server

The server speaks MCP over stdio. The data directory is resolved from the
`SOCCER_DATA_DIR` env var, the first CLI argument, or by searching up from the
executable for `data/kaggle`.

```bash
dotnet run --project src/BrazilianSoccer.Server
```

Example MCP client config (launches the server as a subprocess):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "src/BrazilianSoccer.Server"],
      "env": { "SOCCER_DATA_DIR": "/abs/path/to/data/kaggle" }
    }
  }
}
```

## Data quality notes

- The FIFA player dataset is a fixed ~2019 snapshot. Top players carry real
  names (Neymar Jr, Casemiro), but coverage of Brazilian-league squads is
  partial and some lower-tier club rosters use placeholder names; a few clubs
  (e.g. Flamengo) are absent entirely. Player queries return exactly what that
  file contains; the match data is independent and complete.
- Statistics and standings are computed only from matches that have a recorded
  score; rows with missing goals are excluded from aggregation.

## Specification

[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
