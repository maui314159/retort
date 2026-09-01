# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian soccer. It loads the six Kaggle datasets in `data/kaggle/`
into a normalized in-memory knowledge graph and exposes it to any MCP client
(Claude Desktop, Cursor, etc.) over stdio.

## What it answers

| Category | Example questions | Tools |
|----------|-------------------|-------|
| Match queries | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find Copa Libertadores finals" | `search_matches` |
| Team queries | "What is Corinthians' home record in 2022?", "Compare Palmeiras and Santos head-to-head" | `team_statistics`, `team_comparison`, `team_overview` |
| Player queries | "Who is Neymar?", "Find all Brazilian players", "Who are the highest-rated players at Grêmio?" | `search_players`, `player_profile` |
| Competition queries | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" | `league_standings`, `competition_statistics`, `biggest_wins` |
| Statistical analysis | "What's the average goals per match?", "Which team has the best away record?", head-to-head records | `head_to_head`, aggregates above |
| Knowledge graph | "Which nodes relate to Flamengo?", "Who plays for PSG?" | `search_knowledge_graph`, `graph_neighbors` |

Standings are computed from match results — the 2019 Brasileirão table comes
out as Flamengo 90 pts (28W 6D 4L), matching the real season.

## Running the server

```bash
python -m brazilian_soccer_mcp          # stdio transport (default)
# or, after `pip install -e .`:
brazilian-soccer-mcp
```

MCP client configuration (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp"],
      "env": {}
    }
  }
}
```

Datasets load once at startup (~3-5 s); afterwards every tool responds from
the indexed in-memory model in well under a second.

## Architecture

```
brazilian_soccer_mcp/
  normalize.py        team-name canonicalization, date/number parsing
  data_loader.py      unified loader for the 6 CSVs + indexes + dedupe
  knowledge_graph.py  in-memory property graph (teams, players, clubs,
                      competitions, matches + relationships)
  queries.py          query engine (the 5 capability categories)
  server.py           MCP tool definitions (official `mcp` SDK)
  __main__.py         `python -m` entry point
features/             BDD (Gherkin) feature files
tests/                pytest-bdd step definitions + unit tests
```

### Data handling highlights

- **Team name normalization** — "Palmeiras-SP", "Palmeiras - SP" and
  "Palmeiras" collapse to one team; accents fold ("Sao Paulo" → "São Paulo");
  club prefixes and commentaries are stripped; the three *Atleticos*,
  América-MG/RN, Nacional-AM/Uruguay and Vitória/Vitória-ES stay distinct.
  ~200 alias entries map known variants to canonical names.
- **Date formats** — ISO, ISO-with-time and Brazilian DD/MM/YYYY all parse to
  ISO `YYYY-MM-DD`; "NA"/"-"/empty are treated as unknown.
- **De-duplication with enrichment** — the match files overlap heavily
  (e.g. Brasileirão 2012-2019 in three files). Fixtures are keyed on
  (competition, date, teams) with a ±3-day second pass for shifted dates;
  duplicates enrich the kept record with arena names and corners/shots/
  attacks instead of double counting. Result: a complete 380-match Série A
  for every season 2012-2022 and correct historical seasons from 2003.
- **Cross-file linkage** — FIFA clubs that match a match-data team are linked
  via `SAME_AS`, so `team_overview` combines match records with squad data.

## Testing

```bash
venv/bin/python -m pytest          # 135 tests
```

- **BDD (pytest-bdd)** — Gherkin scenarios in `features/` mirror the
  specification's testing approach: match, team, player, competition and
  statistical-analysis features, with step definitions in `tests/steps/`.
- **Unit tests** — normalization table (team variants, dates, numbers),
  loader coverage/dedupe/enrichment, knowledge-graph structure, and
  end-to-end MCP tool calls.
- **Protocol smoke test** — the server is exercised over real JSON-RPC
  (initialize → tools/list → tools/call) during development; see
  `tests/test_server_tools.py` for the tool-level equivalent.

## Data sources

All datasets ship in `data/kaggle/` (see `README` section below for licenses):

- `Brasileirao_Matches.csv` — Série A 2012-2022 (CC BY 4.0)
- `Brazilian_Cup_Matches.csv` — Copa do Brasil 2012-2021 (CC BY 4.0)
- `Libertadores_Matches.csv` — Copa Libertadores 2013-2021 (CC BY 4.0)
- `BR-Football-Dataset.csv` — extended stats 2014-2023 (CC0)
- `novo_campeonato_brasileiro.csv` — historical Série A 2003-2019 (CC BY 4.0)
- `fifa_data.csv` — FIFA player database, 18,207 players (Apache 2.0)

Optional external APIs (API-Football, TheSportsDB, Wikipedia/DBpedia) from the
specification are not integrated; all required capabilities are served from
the provided data alone.
