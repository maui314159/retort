# Brazilian Soccer MCP Server (C#)

An [MCP](https://modelcontextprotocol.io) server that exposes a queryable
knowledge base of Brazilian soccer — matches, teams, players, competitions, and
aggregate statistics — built over the Kaggle datasets in `data/kaggle/`. It
speaks MCP over stdio and is intended to be connected to an LLM client.

## Solution layout

| Project | Purpose |
|---------|---------|
| `src/BrazilianSoccer.Core` | CSV loading, team-name normalization, the query engine, and text formatting. No MCP/host dependencies. |
| `src/BrazilianSoccer.Mcp`  | MCP host (stdio) exposing the engine as MCP tools via the `ModelContextProtocol` SDK. |
| `tests/BrazilianSoccer.Tests` | xUnit BDD (Given/When/Then) tests over the real datasets. |

## Build, test, run

```bash
dotnet build            # build all projects
dotnet test             # run the BDD test suite (loads the real CSVs once)
dotnet run --project src/BrazilianSoccer.Mcp   # start the stdio MCP server
```

The server locates `data/kaggle/` by walking up from the executable / working
directory. Override with the `BRSOCCER_DATA_ROOT` environment variable (point it
at the repository root). All logging goes to stderr so stdout stays a clean MCP
JSON-RPC channel.

## MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches" (includes head-to-head when two teams given) |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `find_players` | "Find all Brazilian players", "Who plays for Real Madrid?" |
| `player_profile` | "Who is L. Messi?" |
| `standings` | "Who won the 2019 Brasileirão?" (table calculated from match results) |
| `competition_stats` | "What's the average goals per match?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `top_scoring_teams` | "Which team scored the most goals in Serie A 2019?" |
| `best_away_records` | "Which team has the best away record?" |
| `dataset_overview` | What data is loaded (matches, players, seasons, competitions) |

## Data handling

- **Team-name normalization.** Names appear with state suffixes ("Palmeiras-SP"),
  country codes ("Nacional (URU)"), accents ("São Paulo", "Grêmio"), and varying
  case. A loose key (suffix-stripped, accent-folded, lower-cased) drives search;
  a stronger *identity key* that keeps the suffix drives aggregation so distinct
  clubs that share a loose key (Atlético-MG vs Athletico-PR) are never merged.
- **Cross-source deduplication.** The five match CSVs overlap heavily — e.g. 2019
  Série A appears in three files with divergent team names and even divergent
  match dates. Per `(competition, season)` bucket the loader keeps rows from only
  the single highest-priority source (dedicated per-competition file > historical
  file > generic multi-competition file). This reproduces the real season tables:
  the calculated 2019 Brasileirão standings match history (Flamengo 90 pts,
  28W-6D-4L).
- **Tolerant parsing.** Goals stored as `NA`/blank are treated as "no result" and
  excluded from standings and aggregates; dates are parsed from ISO, ISO+time,
  and Brazilian `DD/MM/YYYY` formats; files are read as BOM-tolerant UTF-8.

## Testing

xUnit tests follow the spec's Given/When/Then scenarios and assert behavioral
invariants (W+D+L equals matches played, head-to-head symmetry under argument
swap, standings points = 3·W+D, NA rows excluded, multi-format date parsing,
dedup yields exactly 20 teams / 380 matches for 2019 Série A) rather than brittle
raw counts.

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
