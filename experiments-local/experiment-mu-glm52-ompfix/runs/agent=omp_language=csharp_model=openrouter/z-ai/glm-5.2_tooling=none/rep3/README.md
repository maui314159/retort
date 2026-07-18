# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph style query
interface over six Kaggle Brazilian-soccer datasets. An LLM client (Claude,
Copilot, etc.) connects to the server over stdio and calls tools to answer
natural-language questions about players, teams, matches, competitions, and
statistics.

Built in **C# / .NET 10** with the official
[ModelContextProtocol C# SDK](https://csharp.sdk.modelcontextprotocol.io) and
[CsvHelper](https://joshclose.github.io/CsvHelper/).

## What it does

Loads all six CSV files into memory once at startup, normalizes team names and
competition names so a single query transparently spans every file, and exposes
**10 MCP tools** (snake_cased on the wire):

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range |
| `head_to_head` | Head-to-head record + fixture list between two teams |
| `team_statistics` | W/D/L, goals, win rate; filter by season, competition, venue (home/away) |
| `team_competitions` | All competitions a team has appeared in |
| `search_players` | Search the FIFA DB by name, nationality, club, position, min rating |
| `brazilian_players_at_brazilian_clubs` | Brazilian players grouped by Brazilian club |
| `competition_standings` | Computed league standings (champion + relegated flagged) |
| `biggest_wins` | Largest goal-margin victories |
| `average_goals` | Avg goals/match + home/away/draw percentages |
| `derbies` | Classic Brazilian clássicos (Fla-Flu, Gre-Nal, Majestoso, …) for a season |

### Data sources (all in `data/kaggle/`)

| File | Coverage |
|------|----------|
| `Brasileirao_Matches.csv` | Série A 2012–2022 (with rounds) |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil 2012–2021 |
| `Libertadores_Matches.csv` | Copa Libertadores 2013–2022 (with stage) |
| `BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil 2014–2023 (extended stats) |
| `novo_campeonato_brasileiro.csv` | Série A historical 2003–2019 |
| `fifa_data.csv` | FIFA player database (18,207 players) |

### Data-quality handling

- **Team name variations** — the datasets use state-suffixed (`Palmeiras-SP`),
  spaced (`Botafogo RJ`), parenthetical (`Nacional (URU)`), full-name
  (`Atletico Mineiro`), and accented vs non-accented variants. `TeamNormalizer`
  reduces every name to one canonical key (state suffix stripped & validated
  against the 27 UF codes, diacritics removed). The **Atlético cluster** (MG/PR/GO
  are genuinely distinct famous clubs) keeps its state in the key and unifies the
  `Atletico`/`Athletico` spellings + full names.
- **Cross-file deduplication** — Série A 2014–2022 appears in both the Brasileirao
  and BR-Football files. The repository deduplicates matches by
  `(date, homeKey, awayKey, goals)`, keeping the richer/curated source so counts
  and head-to-head tallies are not inflated.
- **Date formats** — handles ISO (`yyyy-MM-dd HH:mm:ss`), date-only, and Brazilian
  (`dd/MM/yyyy`) formats. **UTF-8** encoding is used throughout for accented names.

## Project structure

```
BrazilianSoccerMcp/
├── Program.cs                  # MCP host: DI, stdio transport, data-dir resolution
├── Models.cs                   # Match, Player, TeamStat, DisplayCandidate
├── TeamNormalizer.cs           # Canonical team-key + display-name normalization
├── SoccerDataRepository.cs     # Loads all 6 CSVs; query/aggregate/standings engine
└── Tools/SoccerTools.cs        # 10 [McpServerTool] methods (the LLM-facing API)

BrazilianSoccerMcp.Tests/        # xUnit BDD (Given/When/Then) tests
├── TestBase.cs
├── MatchQueryTests.cs          # Feature: Match Queries
├── TeamQueryTests.cs           # Feature: Team Queries
├── PlayerQueryTests.cs         # Feature: Player Queries
└── CompetitionQueryTests.cs   # Feature: Competition Queries & Statistical Analysis
```

Every code file opens with a context-block comment explaining what it does and why.

## Build & run

```bash
dotnet build BrazilianSoccerMcp.slnx
dotnet test BrazilianSoccerMcp.slnx           # 35 BDD tests, all green
dotnet run --project BrazilianSoccerMcp        # starts the stdio MCP server
```

The data directory is auto-discovered by walking up from the working directory
until `data/kaggle/Brasileirao_Matches.csv` is found; override with the
`SOCCER_DATA_DIR` environment variable.

### Connect from an MCP client

The server runs over stdio. Point any MCP-compatible client at the built
executable, e.g. a `claude_desktop_config.json` entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/BrazilianSoccerMcp",
      "env": { "DOTNET_ROOT": "/path/to/dotnet/runtime" }
    }
  }
}
```

## Testing

BDD-style (Given/When/Then) xUnit tests, 35 scenarios across the five capability
categories from the spec. Run from the repo root:

```bash
dotnet test
```

Sample questions the server answers (via the tools above): "Show me all
Flamengo vs Fluminense matches", "What is Corinthians' home record in 2022?",
"Who are the highest-rated Brazilian players?", "Who won the 2019 Brasileirão?",
"What's the average goals per match in the Brasileirão?", "Show me the biggest
wins", "Show all derbies in 2019".
