# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
turns six Kaggle datasets about Brazilian soccer into a small knowledge
graph an LLM can query: matches, clubs, players, standings, head-to-head
records, derbies and aggregate statistics.

Implemented in pure Python (standard library only - no runtime
dependencies), per `TASK.md` / `brazilian-soccer-mcp-guide.md`.

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

## What was implemented

| Module | Role |
|---|---|
| `brazilian_soccer_mcp/normalizer.py` | Team-name normalisation (state suffixes, accents, full names, aliases, dotted abbreviations, country suffixes), dominant-region resolution for stateless names, competition aliases, multi-format date/goal/money parsing. |
| `brazilian_soccer_mcp/loader.py` | Loads all six CSVs, repairs known data errors, merges duplicate fixtures across sources, builds the club registry and all query indexes. |
| `brazilian_soccer_mcp/models.py` | `Match` / `Player` / `Club` / `StandingRow` dataclasses with JSON-ready `to_dict()`. |
| `brazilian_soccer_mcp/queries.py` | Every capability in the spec: match search, last meeting, head-to-head, team stats/profile, standings, biggest wins, aggregate stats, best records, derbies, player search, player-club report, competition/team directories. |
| `brazilian_soccer_mcp/render.py` | Human-formatted answers (the formats shown in the spec's examples), shared by MCP tools and the CLI. |
| `brazilian_soccer_mcp/tools.py` | The 14 MCP tool descriptors (JSON-Schema inputs) and their dispatch. |
| `brazilian_soccer_mcp/server.py` | MCP stdio server: newline-delimited JSON-RPC 2.0, implemented directly on the standard library. |
| `brazilian_soccer_mcp/cli.py` | Direct command-line access to the same queries. |

### Data engineering notes

The five match files overlap heavily (the 2019 Brasileirão appears in three
of them) and disagree on spellings, so the loader:

- **Deduplicates league fixtures** to exactly one row per
  (season, home, away) orientation, preferring the primary source
  (`Brasileirao_Matches.csv` > historical > BR-Football) and a played row
  over an `'NA'` (unplayed) row. Result: every Série A season 2006-2022
  has exactly 380 matches (2009: 379 - a duplicated row in the source;
  2023: 377 - the BR-Football file is three short).
- **Deduplicates cup fixtures** by score-equality plus a <=2-day date
  window, since the same clubs can legitimately meet twice in a season.
- **Repairs known source errors**: the historical file tags Bahia as UF
  "BH" and Vitória as "ES" (both wrong); BR-Football mislabels some Série B
  fixtures as "Serie A" (relegated clubs appearing in the wrong season) and
  includes stray state-league rows (e.g. Suzano-SP's single "2019 Serie B"
  match) - both patterns are detected and dropped.
- **Treats `'NA'`/`'-'` goals as scheduled-but-unplayed**: they appear in
  fixture lists but never in statistics.
- **Resolves every team spelling** ("Palmeiras-SP" = "Palmeiras" = "Sport
  Club Corinthians Paulista", "Athletico Paranaense" = "Atletico-PR",
  "Atlético Mineiro" = "Atletico-MG") and disambiguates stateless names by
  dominance ("Santos" -> Santos-SP, not Santos-AP).

### Tools exposed (MCP `tools/list`)

`search_matches`, `last_match_between`, `head_to_head`, `team_stats`,
`team_profile`, `standings`, `biggest_wins`, `competition_stats`,
`best_records`, `derbies`, `player_search`, `player_club_report`,
`list_competitions`, `list_teams`

Resources (`resources/list`) expose a dataset overview, the competitions
index, the club directory and one metadata page per source CSV.

## Running

```bash
# MCP server over stdio (what an MCP client spawns)
python -m brazilian_soccer_mcp

# Direct CLI (same queries, human-formatted output)
python -m brazilian_soccer_mcp.cli standings serie_a 2019
python -m brazilian_soccer_mcp.cli search-matches --team Flamengo --opponent Fluminense
python -m brazilian_soccer_mcp.cli h2h Palmeiras Santos
python -m brazilian_soccer_mcp.cli players --nationality Brazil --limit 5
python -m brazilian_soccer_mcp.cli derbies --season 2023
python -m brazilian_soccer_mcp.cli tools
```

Register with an MCP client (example for Claude-style config):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp"],
      "cwd": "/path/to/this/repository"
    }
  }
}
```

Set `BRAZILIAN_SOCCER_DATA_DIR` to point at another copy of the six CSVs.

## Testing

BDD/GWT-structured pytest suite (Given/When/Then docstrings, one feature
module per TASK.md capability):

```bash
python -m pytest          # 148 scenarios, ~4s
```

- `tests/test_normalizer.py` - name/competition/date normalisation
- `tests/test_loader.py` - loading, dedup, registry, performance criteria
- `tests/test_queries_matches.py` - Feature: Match Queries
- `tests/test_queries_teams.py` - Feature: Team Queries
- `tests/test_queries_players.py` - Feature: Player Queries
- `tests/test_queries_competitions.py` - Feature: Competition Queries
- `tests/test_queries_stats.py` - Feature: Statistical Analysis
- `tests/test_sample_questions.py` - the spec's sample questions, end to end
- `tests/test_server.py` - MCP protocol (handshake, tools, resources,
  error codes) plus a real client session over pipes

Performance (TASK.md criteria): dataset load ~0.8s once per process;
simple lookups answer in single-digit milliseconds; aggregate queries in
milliseconds - comfortably inside the 2s/5s budgets (asserted in the
suite).
