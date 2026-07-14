# Brazilian Soccer MCP Server (C# / .NET 10)

A Model Context Protocol (MCP) server that exposes the bundled Brazilian
soccer CSV datasets to an LLM through a JSON-RPC 2.0 stdio transport.
LLM clients can ask natural-language questions about matches, teams,
players, and competition standings; the server answers by running
typed queries against an in-memory dataset.

See `TASK.md` and `brazilian-soccer-mcp-guide.md` for the full specification.

---

## What's implemented

- **All 6 datasets load and are queryable:**
  - `Brasileirao_Matches.csv` (Serie A, with state-suffixed team names)
  - `Brazilian_Cup_Matches.csv` (Copa do Brasil)
  - `Libertadores_Matches.csv`
  - `BR-Football-Dataset.csv` (extended stats: corners, shots, attacks, HT result)
  - `novo_campeonato_brasileiro.csv` (2003-2019 Brasileirão)
  - `fifa_data.csv` (18,207 players, 70+ attributes)
- **Team name normalization** for the cross-dataset naming chaos:
  - With / without state suffix: `Flamengo-RJ` ⇔ `Flamengo`
  - Punctuation variants: `Flamengo - RJ` ⇔ `Flamengo (RJ)` ⇔ `Flamengo`
  - Accent / no-accent: `São Paulo` ⇔ `Sao Paulo`
- **Multi-format date parsing** (ISO, Brazilian DD/MM/YYYY, with optional time)
- **UTF-8 throughout** -- team names like `Grêmio`, `São Paulo`, `Avaí`
  survive end-to-end.
- **13 MCP tools** covering all five query categories from the spec.
- **46 BDD tests** (xUnit + FluentAssertions) -- all green.

## MCP tools exposed

| Category | Tool |
|---|---|
| Match queries | `find_matches_by_team`, `find_head_to_head`, `last_match_between` |
| Team queries | `get_team_record`, `get_standings` |
| Player queries | `search_players`, `players_by_club`, `top_brazilian_players`, `forwards_at_club` |
| Statistical analysis | `average_goals_per_match`, `home_win_rate`, `biggest_wins`, `best_away_records` |

Plus the standard MCP methods `initialize` and `tools/list`.

## Solution layout

```
src/
  BrazilianSoccerMcp.Core/         Class library -- data loaders, query engine, models
    Models/                        MatchRecord, PlayerRecord, TeamRecord, etc.
    Data/                          One CSV loader per dataset + DateTimeParser
    Dataset.cs                     Loads all CSVs into one immutable in-memory store
    QueryEngine.cs                 Pure read API; one method per tool
    TeamNameNormalizer.cs          Diacritic + state-suffix normalization
  BrazilianSoccerMcp.Server/       Console app -- stdio JSON-RPC 2.0 MCP server
    Program.cs                     Process entry point
    McpStdioServer.cs              Line-buffered JSON-RPC loop
    ToolRegistry.cs                Tool catalog, JSON-schema generation, invocation glue
tests/
  BrazilianSoccerMcp.Tests/        xUnit BDD tests, 46 scenarios
    TestDataFixture.cs             Loads the dataset once for the whole assembly
    MatchQueriesTests.cs           "Find matches by team/date/season/competition"
    TeamQueriesTests.cs            "Home record", "H2H", "best home/away record"
    PlayerQueriesTests.cs          "Search players", "by club", "Brazilian players"
    CompetitionQueriesTests.cs     "Who won 2019?", "standings invariants"
    StatisticalAnalysisTests.cs    "Average goals", "home win rate", "biggest wins"
    TeamNameNormalizerTests.cs     Normalizer unit tests (variations, accents, parens)
    McpServerTests.cs              End-to-end JSON-RPC tests against a child server
```

## Build and run

Requires the .NET 10 SDK (`dotnet --version` should report 10.0.x or newer).

```bash
# Restore + build
dotnet build

# Run the test suite
dotnet test

# Launch the MCP server (reads JSON-RPC from stdin, writes to stdout)
dotnet run --project src/BrazilianSoccerMcp.Server
```

The server loads the dataset once at startup. Progress messages go to
stderr; the JSON-RPC stream on stdout is reserved for responses.

## Example MCP session

```bash
# Initialize
$ echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    | dotnet run --project src/BrazilianSoccerMcp.Server --no-build
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",
  "serverInfo":{"name":"brazilian-soccer-mcp","version":"1.0.0"},
  "capabilities":{"tools":{}}}}

# Call a tool
$ echo '{"jsonrpc":"2.0","id":2,"method":"tools/call",
    "params":{"name":"find_head_to_head",
              "arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}' \
    | dotnet run --project src/BrazilianSoccerMcp.Server --no-build
{"jsonrpc":"2.0","id":2,"result":{"content":[
  {"type":"text","text":"Flamengo - RJ vs Fluminense - RJ (H2H): Flamengo - RJ 22W, ..."}
],"isError":false}}
```

## Performance

- All data is in memory; simple lookups return in <50 ms.
- Aggregate queries over the full corpus (40k+ rows) run in <500 ms.
- The 5-second aggregate-query target from the spec is met with margin
  on the included datasets.

## Data attribution

The bundled CSVs come from public Kaggle sources and remain under
their original licenses (CC BY 4.0 / CC0 / Apache 2.0 -- see
`brazilian-soccer-mcp-guide.md` for per-file attribution).
