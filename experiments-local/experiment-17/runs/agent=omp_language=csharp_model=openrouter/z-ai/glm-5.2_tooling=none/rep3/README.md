# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that exposes the bundled Kaggle Brazilian
football datasets (matches, competitions, and the FIFA player database) as tools
an LLM can call to answer natural-language questions about Brazilian soccer.

Implemented in **C# / .NET 10** using the official
[`ModelContextProtocol`](https://github.com/modelcontextprotocol/csharp-sdk) C#
SDK over **stdio transport**. Behaviour is verified with BDD-style
Given/When/Then xUnit tests run against the real datasets.

## Project layout

```
BrazilianSoccerMcp.slnx
src/BrazilianSoccerMcp/              # The MCP server (console app)
  Models/                            # Match, Player, Competition, TeamStats
  Data/                              # CsvReader, SoccerDataLoader, TeamNormalizer, DataLocator
  Services/SoccerQueryService.cs     # Pure-logic query + aggregation engine
  Tools/SoccerTools.cs               # [McpServerTool] surface (10 tools)
  Program.cs                         # stdio MCP host
tests/BrazilianSoccerMcp.Tests/      # BDD xUnit tests (42 scenarios)
data/kaggle/                         # The six bundled CSV datasets
```

## Datasets used (all in `data/kaggle/`)

| File | Records | Role |
|------|---------|------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Serie A 2012-2022 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores |
| `BR-Football-Dataset.csv` | 10,296 | Extended match statistics (Serie A/B/C, Copa do Brasil) |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão 2003-2019 |
| `fifa_data.csv` | 18,207 | FIFA player database |

## MCP tools (10)

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, date range |
| `last_match` | Most recent match for a team (optionally vs an opponent) |
| `head_to_head` | Head-to-head record + fixture list between two teams |
| `team_statistics` | Win/draw/loss + goals tally, by competition/season/venue |
| `team_competitions` | Competitions a team has appeared in |
| `competition_standings` | League standings by points from match results |
| `biggest_wins` | Largest winning margins |
| `goals_analysis` | Average goals + home/away/draw rate analysis |
| `search_players` | FIFA database search (name, nationality, club, position, rating) |
| `top_players` | Top-rated players by nationality/club |

## Key design decisions

- **Team-name normalisation** (`Data/TeamNormalizer.cs`): the datasets use
  state-suffixed (`Palmeiras-SP`), parenthetical-annotated
  (`Boavista SC (antigo EC Barreira) - RJ`), full (`Atlético Mineiro`) and
  ASCII-stripped (`Sao Paulo`) forms. A naive "strip the trailing state code"
  normaliser **collides** short-named clubs (`Atletico-MG` / `Atletico-PR` /
  `Atletico-GO` all collapse to `atletico`; `América-MG` / `América-RN` to
  `america`), which corrupts standings and head-to-head aggregates. The
  normaliser therefore **keeps the state suffix** and layers a curated alias map
  for the ~35 major Brazilian clubs mapping every variant (suffixed short form,
  full Portuguese name, FIFA form) to one canonical display name. Verified by a
  dedicated anti-collision test.
- **Competition routing**: `Brasileirão` standings for seasons 2003-2011 auto-
  route to the historical 2003-2019 dataset (the modern Serie A CSV starts in
  2012), so one competition name answers both eras.
- **Cross-file queries**: `search_matches` and `biggest_wins` span every match
  dataset, so e.g. "Palmeiras matches in 2023" is answered by the extended-stats
  dataset even though the modern Serie A CSV ends in 2022.
- **Lazy loading**: datasets are parsed once on first tool call and cached for
  the process lifetime; logging goes to stderr so stdout stays clean for MCP
  JSON-RPC framing.

## Build & test

```bash
dotnet build BrazilianSoccerMcp.slnx
dotnet test tests/BrazilianSoccerMcp.Tests/BrazilianSoccerMcp.Tests.csproj
```

The 42 BDD tests assert real, verifiable facts against the bundled data, e.g.:

- 2019 Brasileirão standings → Flamengo champion with **90 pts**, Santos & Palmeiras 74.
- `Atletico-MG` / `Atletico-PR` / `Atletico-GO` resolve to three **distinct** clubs.
- Top Brazilian player → **Neymar Jr, Overall 92**; 827 Brazilian players; 20 players per present Brazilian club.
- Head-to-head win/draw/loss tallies sum to total matches; goal-analysis rates sum to 1.0.

## Run the MCP server

```bash
dotnet run --project src/BrazilianSoccerMcp
```

The server speaks MCP over stdio. Add it to an MCP client (e.g. Claude Desktop)
with a command such as:

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

Sample tool output (`competition_standings`, Brasileirão 2019):

```
20 teams in Brasileirão 2019 standings:

 1. Flamengo - 90 pts (28W, 6D, 4L, GF 86, GA 37) - Champion
 2. Santos - 74 pts (22W, 8D, 8L, GF 60, GA 33)
 3. Palmeiras - 74 pts (21W, 11D, 6L, GF 61, GA 32)
 4. Grêmio - 65 pts (19W, 8D, 11L, GF 64, GA 39)
 5. Athletico Paranaense - 64 pts (18W, 10D, 10L, GF 51, GA 32)
```

## Licenses

Data licenses are per-source (CC BY 4.0, CC0, Apache 2.0) — see `TASK.md` /
`brazilian-soccer-mcp-guide.md` for attribution. Server code is original.
