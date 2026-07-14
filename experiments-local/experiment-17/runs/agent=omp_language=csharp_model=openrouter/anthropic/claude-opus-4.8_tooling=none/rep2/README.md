# Brazilian Soccer MCP Server (C#)

An [MCP](https://modelcontextprotocol.io) server that exposes a queryable
knowledge graph over Brazilian-soccer datasets (matches, teams, players,
competitions) so an LLM client can answer natural-language questions about
Brazilian football. Implemented in C# on .NET 10.

## Solution layout

| Project | Purpose |
|---------|---------|
| `src/BrazilianSoccer.Core` | Domain models, RFC 4180 CSV reader, team-name normalizer, data loader, query engine, response formatter. |
| `src/BrazilianSoccer.Server` | MCP stdio host (`brazilian-soccer-mcp`) exposing the query capabilities as MCP tools. |
| `tests/BrazilianSoccer.Tests` | xUnit BDD (Given/When/Then) tests over the real datasets. |

## Build & test

```bash
dotnet test BrazilianSoccer.sln      # build everything + run all tests
dotnet run --project src/BrazilianSoccer.Server   # start the MCP stdio server
```

The server locates `data/kaggle` by walking up from the working directory;
override with the `SOCCER_DATA_DIR` environment variable.

## MCP client configuration

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "src/BrazilianSoccer.Server"]
    }
  }
}
```

## Tools

| Tool | Answers |
|------|---------|
| `find_matches` | Matches by team, competition, season, date range. |
| `matches_between` | All matches between two teams + head-to-head. |
| `last_match` | Most recent meeting of two teams and its score. |
| `team_record` | Win/draw/loss + goals, optionally by competition/season/venue. |
| `compare_teams` | Head-to-head summary between two teams. |
| `search_players` | FIFA players by (partial) name. |
| `players_by_nationality` | Players of a nationality (e.g. Brazil), top-rated first. |
| `players_by_club` | Players at a club (e.g. Flamengo). |
| `top_players` | Highest-rated players, filterable by nationality/position. |
| `standings` | League table for a competition+season, calculated from results. |
| `champion` | Champion of a competition+season. |
| `statistics` | Avg goals/match, home/away win rate, draw rate for a slice. |
| `biggest_wins` | Matches with the largest goal margins. |
| `top_scoring_teams` | Teams ranked by goals scored. |

## Data handling notes

- **Six CSV files** are loaded into a unified `Match`/`Player` model.
- **Team-name normalization** reconciles state suffixes (`Palmeiras-SP`),
  country codes (`Nacional (URU)`), accents (`São Paulo`, `Grêmio`) and full
  legal names (`Sport Club Corinthians Paulista`).
- **Multiple date formats** (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`)
  and UTF-8 (including a BOM on `fifa_data.csv`) are handled.
- **Source de-overlap:** Serie A 2012–2019 and Copa do Brasil seasons appear in
  several files. For each `(competition, season)` the loader keeps only the
  single most authoritative source, so standings/statistics are not
  double-counted. Verified: the calculated 2019 Brasileirão has 20 teams,
  38 games each, champion **Flamengo – 90 pts (28W, 6D, 4L)**.

## Testing

BDD Given/When/Then xUnit tests cover the CSV reader, the team-name normalizer,
and the match / team / player / competition / statistics query capabilities
against the real datasets (47 tests).

---

# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

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
