# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes the bundled Kaggle Brazilian-soccer datasets as tools an LLM can call
to answer natural-language questions about players, teams, matches, and
competitions.

Implemented in C# / .NET 10 using the official
[ModelContextProtocol C# SDK](https://github.com/modelcontextprotocol/csharp-sdk).

---

## What was built

| Layer | Files | Responsibility |
|-------|-------|----------------|
| Models | `src/BrazilianSoccerMcp/Models/{Match,Player,Competition}.cs` | Unified `Match`/`Player` records + `Competition` enum |
| Data | `src/BrazilianSoccerMcp/Data/TeamNameNormalizer.cs` | Canonical team-name key (state-suffix/diacritics/club-form stripping) |
| Data | `src/BrazilianSoccerMcp/Data/SoccerDataStore.cs` | Loads all 6 CSVs into memory via CsvHelper |
| Data | `src/BrazilianSoccerMcp/Data/SoccerQueryService.cs` | All analytics: match filters, H2H, standings, goals overview, biggest wins, player search |
| Data | `src/BrazilianSoccerMcp/Data/QueryDtos.cs` | Result DTOs (`TeamStats`, `HeadToHead`, `StandingRow`, `GoalsOverview`) |
| Tools | `src/BrazilianSoccerMcp/Tools/SoccerTools.cs` | 11 `[McpServerTool]` methods returning human-readable strings |
| Host | `src/BrazilianSoccerMcp/Program.cs` | stdio MCP host with data-dir resolution |
| Tests | `tests/BrazilianSoccerMcp.Tests/Bdd*.cs` | 53 BDD Given/When/Then tests over the real CSVs |

### Datasets loaded

All 6 datasets in `data/kaggle/` are loaded at startup into memory:

| File | Rows | Competition key |
|------|------|-----------------|
| `Brasileirao_Matches.csv` | 4,180 | `brasileirao` |
| `Brazilian_Cup_Matches.csv` | 1,337 | `copa_do_brasil` |
| `Libertadores_Matches.csv` | 1,255 | `libertadores` |
| `BR-Football-Dataset.csv` | 10,296 | `br_football` |
| `novo_campeonato_brasileiro.csv` | 6,886 | `historico` |
| `fifa_data.csv` | 18,207 players | — |

### MCP tools (11)

`search_matches`, `head_to_head`, `team_statistics`, `competition_standings`,
`biggest_wins`, `goals_overview`, `search_players`, `top_players`,
`list_competitions`, `list_seasons`, `list_teams`.

Each accepts the filters described in `TASK.md` (team, opponent, competition,
season, date range, venue, nationality, club, position, overall range) and
returns text formatted like the spec's "Example answer format" blocks.

### Team-name normalization

Brazilian club names appear in many forms across the datasets
(`Palmeiras-SP`, `Palmeiras`, `São Paulo-SP`, `Sport Club Corinthians Paulista`,
`Boavista Sport Club (antigo Esporte Clube Barreira) - RJ` …).
`TeamNameNormalizer.NormalizeTeam` reduces every label to a canonical key by:
stripping parentheticals → stripping a trailing state suffix (`-SP`, ` - RJ`) →
lowercasing + removing diacritics → stripping club-form tokens
(`futebol clube`, `sport club`, `esporte clube`, `ec`, `fc`, …) → collapsing
whitespace. Matching is canonical-key containment, so a query for `Palmeiras`
matches `Palmeiras-SP`. Known collisions (e.g. `Botafogo-RJ` vs `Botafogo-SP`
both → `botafogo`) are accepted for this demo.

---

## Build & test

```bash
dotnet build BrazilianSoccerMcp.slnx
dotnet test  BrazilianSoccerMcp.slnx
```

Requirements: .NET 10 SDK. Tests load the real CSVs from `data/kaggle`
(located by walking up from the test bin directory).

### Test results

53 BDD tests across 4 feature files, all passing:

- `BddMatchQueries` — match search by team/opponent/competition/season/date, name normalization
- `BddTeamQueries` — team statistics, venue filtering, head-to-head arithmetic
- `BddPlayerQueries` — FIFA player search by nationality/club/position/name/overall
- `BddCompetitionAndStats` — computed standings, champion/relegation flags, goals overview, biggest wins
- `BddToolsAndNormalization` — MCP tool string output + normalizer edge cases

---

## Run the MCP server

```bash
# The CSVs are copied next to the binary at build time; or point at the repo copy:
export SOCCER_DATA_DIR="$PWD/data/kaggle"
dotnet run --project src/BrazilianSoccerMcp
```

The server speaks JSON-RPC 2.0 over stdio (the standard MCP stdio transport).
Register it with any MCP-compatible client (Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "/path/to/src/BrazilianSoccerMcp", "--"],
      "env": { "SOCCER_DATA_DIR": "/path/to/data/kaggle" }
    }
  }
}
```

### Data directory resolution

`Program.cs` looks for the CSVs in this order:
1. `SOCCER_DATA_DIR` env var
2. `./data/kaggle` relative to the working directory
3. `data/kaggle` next to the binary (populated by the `.csproj` `<None>` copy)
4. ancestor directories (for `dotnet run` from the repo root)

### Smoke test (verified)

Driving the server over stdio with `initialize` → `tools/list` → `tools/call`
returns, for example:

- `list_competitions` → 4180 / 1337 / 1255 / 10296 / 6886 matches, 18207 players
- `top_players` (Brazil, 3) → Neymar Jr 92 LW (PSG), Casemiro 88 CDM (Real Madrid), Coutinho 88 LW (Barcelona)
- `head_to_head` (Flamengo vs Fluminense) → 77 matches, 31 / 25 / 21 wins/draws, with recent fixtures

---

## Architecture notes

- **No external database** — data is read-only and fits comfortably in memory
  (~24k matches, ~18k players); simple lookups are O(n) and return in well under
  the 2-second budget.
- **Analytics are in `SoccerQueryService`, not the tools** — the MCP tool layer
  is a thin formatter so the logic is unit-testable without the host.
- **Defensive parsing** — rows with unparseable scores keep fixture presence but
  get null goals and are excluded from goal aggregates by `Match.HasScore`.
- **Standings** are computed from match results (3 pts/win, 1/draw), sorted by
  points → goal difference → goals for; row 1 is flagged `Champion`, the bottom
  4 of a ≥20-team league are flagged `Relegated`.

## Data sources & licenses

See `README.md` (original) and `TASK.md` for the Kaggle dataset attributions
(CC BY 4.0, CC0, Apache 2.0). All data is pre-downloaded in `data/kaggle/`.
