# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that answers
natural-language questions about Brazilian soccer: matches (Brasileirão
Serie A/B/C, Copa do Brasil, Copa Libertadores), team records and standings,
head-to-head comparisons, and a FIFA player database.

Implements the specification in `TASK.md` (a.k.a. `brazilian-soccer-mcp-guide.md`).

## Quick start

```bash
# run the MCP stdio server (stdlib only, no third-party dependencies)
./venv/bin/python server.py

# inspect the exposed tools
./venv/bin/python server.py --list-tools

# call one tool directly, without an MCP client
./venv/bin/python server.py --invoke standings --args '{"competition": "brasileirao", "season": 2019}'
```

Register it with any MCP client, e.g. for Claude Desktop:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

Protocol support: `initialize`, `ping`, `tools/list`, `tools/call`,
`resources/list`, `resources/read`, `prompts/list`, batched messages and
correct JSON-RPC 2.0 error codes for malformed traffic.

## Tools (12)

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "Palmeiras matches in 2023", matches by date range / competition / stage / source file |
| `head_to_head` | "Compare Palmeiras and Santos", "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2019?", "What competitions has Palmeiras played in?" |
| `team_rankings` | "Which team has the best away record?", "Who scored most goals in Serie A 2019?" |
| `find_team` | Resolves any spelling ("SE Palmeiras", "Grêmio", "America-MG" vs "America-RN") to club entities |
| `search_players` | "Find all Brazilian players", "highest-rated players at Grêmio", "forwards from Santos" |
| `player_detail` | "Who is Gabriel Jesus?" (full FIFA profile) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2019?" |
| `competition_info` | Season coverage and source files per competition |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `stats_summary` | "What's the average goals per match in the Brasileirão?", "Compare 2018 and 2019" |
| `derby_matches` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Majestoso, ...) |

## Architecture

```
server.py                    MCP stdio entry point (+ --list-tools / --invoke test modes)
brazilian_soccer/
  normalize.py               team-name / date / number normalization (the heart of data quality)
  models.py                  Match / Player / TeamEntity dataclasses
  repository.py             loads all 6 CSVs, resolves entities, dedupes, merges stats, indexes
  queries.py                 the 12 query capabilities as plain functions
  tools.py                   JSON-Schema tool registry bound to the queries
  protocol.py               JSON-RPC 2.0 over stdio (MCP transport)
tests/                       BDD (Given/When/Then) pytest suite
```

### Data engineering decisions

- **Team entity resolution.** The datasets spell one club many ways
  ("Palmeiras-SP", "Palmeiras", "SE Palmeiras", "Grêmio" vs "Gremio-RS",
  "Athletico-PR" vs "Atlético-PR", "Nacional (URU)" vs "Nacional-URU"). Every
  spelling is reduced to a stable (base, state/country) identity; clubs that
  share a name are disambiguated by state (`America-MG` vs `America-RN`,
  `Botafogo-RJ` vs `Botafogo-PB`), and bare names of big clubs are pinned to
  their home state so a small Serie C namesake (`Flamengo-PI`) can never split
  or pollute the big club's record.
- **De-duplication.** Three files overlap heavily (the 2012-2019 Brasileirão
  exists in three of them). For every (competition, season) exactly one source
  is preferred (round-by-round files first, the statistics file last);
  duplicate rows from demoted sources are dropped, while their extended
  statistics (corners, shots, attacks) and stadium names are merged into the
  kept match. 23,854 raw rows curate down to 16,612 matches; the raw rows
  remain queryable via `search_matches(source=...)`.
- **Verification against reality.** Standings are computed from match results
  and validated by known facts: champions for 2003/2012/2015/2018/2019/2021/
  2022 all come out right, the 2019 relegation zone (Cruzeiro, CSA,
  Chapecoense, Avaí) matches history, and the 2019 table reproduces the
  spec's example (Flamengo, 90 pts, 28W-6D-4L).
- **Partial data is flagged, not hidden**: the 2022 source stops before the
  final rounds (299/380 matches) and 2023 comes from the statistics file
  only — `standings` reports `data_complete: false` with the counts.

### Known dataset limitations (surfaced, not silently wrong)

- The FIFA table is FIFA 19-era: 827 Brazilians, but only 15 Brazilian clubs
  are licensed (no Flamengo/Palmeiras/Corinthians squads — e.g. "Which
  players play for Flamengo?" honestly returns 0), and Brazilian-league
  player names are pseudonyms. European-based players (Neymar Jr, 92) are
  real. Gabriel Barbosa is simply absent; `player_detail` says so.
- Unplayed fixtures (82 rows in 2022, the 2022 Libertadores final
  placeholder) are skipped and counted in the load report.

## Testing

BDD-style (Given/When/Then) pytest suites, one per capability:

```bash
./venv/bin/python -m pytest                     # 130 tests, ~4 s
./venv/bin/python -m pytest --cov=brazilian_soccer --cov-report=term
```

Includes end-to-end protocol tests that spawn the real server subprocess and
drive the MCP handshake, tool calls, resources and error paths, plus
performance gates (simple lookups < 2 s, aggregates < 5 s).

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

## What was done

Implemented the full TASK.md specification: an MCP server (Python, stdlib
only) exposing 12 tools across the five required capability categories
(match, team, player, competition and statistical queries), with
cross-file team entity resolution, multi-format date parsing, UTF-8
handling, source-preference deduplication with statistic merging, 130
BDD/GWT-structured tests (including end-to-end protocol tests over a real
server subprocess and performance gates), and validation of computed
standings against real-world results.
