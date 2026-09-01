# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server providing a knowledge-graph interface
over Brazilian soccer data: Brasileirão Série A/B/C, Copa do Brasil and Copa
Libertadores matches (2003-2023) plus a FIFA 19 player database (18,207
players). It lets an LLM client answer natural-language questions about
players, teams, matches, competitions and statistics.

Implemented per `brazilian-soccer-mcp-guide.md` / `TASK.md` (spec v2.0).

## Quick start

```bash
source venv/bin/activate          # or: pip install -r requirements.txt
python server.py --info           # print tool inventory
python server.py                  # run the MCP server (stdio transport)
python -m pytest                  # run the full BDD/GWT test suite
```

Register with an MCP client (Claude Desktop, opencode, etc.) using the stdio
command `python server.py` from the repository root.

## Data sources

Kaggle data can't be downloaded without an account so these (freely
available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv (4,180 matches, Série A 2012-2022)
- data/kaggle/Brazilian_Cup_Matches.csv (1,337 matches, Copa do Brasil 2012-2021)
- data/kaggle/Libertadores_Matches.csv (1,255 matches, Libertadores 2013-2022)

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv (10,296 matches with corners/shots/attacks)

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv (6,886 matches, Série A 2003-2019)

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv (18,207 players, FIFA 19 snapshot)

## What was implemented

### Architecture

```
server.py                 MCP server (stdio), 19 tools, JSON answers with
                          a human-formatted "summary" plus structured fields
soccer_mcp/
  models.py               Match / Player / MatchStats / TeamRecord dataclasses
  normalize.py            Unicode/date/name normalization (NFKD accents, ISO
                          and DD/MM/YYYY dates, NA-tolerant numeric parsing)
  clubs.py                Curated registry of ~120 Brazilian clubs with all
                          naming variants + derby registry + fallback
                          identities for foreign/smaller clubs
  loaders.py              CSV loaders for all six files (UTF-8/BOM safe)
  knowledge_graph.py      In-memory property graph: club/player/match/
                          competition nodes; played_home/played_away/won/
                          part_of/plays_for/from_country edges
  engine.py               Query engine: reconciliation, indexes and every
                          query family from the spec
tests/                    BDD Gherkin features + GWT pytest modules
```

### Data reconciliation

The five match files overlap heavily (e.g. Série A 2012-2019 exists in three
files). The engine reconciles them per (competition, season):

- The family-specific Kaggle file is authoritative where it covers a season
  (Brasileirao_Matches > novo for Série A; Brazilian_Cup_Matches for the cup).
- Rows from other files describing the same fixture pairing are merged in;
  BR-Football rows contribute extended statistics (corners/shots/attacks)
  and fill scores the authoritative file is missing (81 unscored 2022
  matches are completed this way). BR-Football date shifts of ±1 day are
  tolerated because pairing, not date, drives the merge.
- Rows describing pairings the authoritative file does not have are dropped
  as mislabelled data (173 rows, e.g. Série B teams mislabelled as Série A
  2021 in BR-Football).
- Seasons not covered by an authoritative file (Série A 2023, Copa do Brasil
  2022-23, Série B/C) keep every row.

Result: 16,712 reconciled matches — Série A 8,403 / Série B 3,677 /
Série C 1,807 / Copa do Brasil 1,570 / Libertadores 1,255.

### Team-name normalization

The datasets write the same club in many ways ("Palmeiras-SP", "Palmeiras",
"SE Palmeiras", "América FC (Minas Gerais)", "A.s.a. - AL", "Athletico"
for Athletico Paranaense in Libertadores). Resolution is layered:

1. A curated alias registry (~120 clubs, ~400 alias forms) maps every
   observed spelling to a canonical club id. Ambiguous base names are
   claimed by the major club only, so "Flamengo" is Flamengo-RJ while
   "Flamengo-PI" stays a distinct club.
2. Foreign Libertadores clubs and small Brazilian clubs fall back to a
   state-stripped identity, so "Luverdense - MT" and "Luverdense" unify
   while "Nacional (URU)" and "Nacional (PAR)" stay distinct.
3. User queries get typo tolerance (difflib) and candidate suggestions
   ("Flamengu" -> did you mean Flamengo?).

### Knowledge graph

An in-memory property graph (36,134 nodes, 98,440 edges) links clubs,
players, matches, competitions and countries. `graph_paths` finds
multi-hop connections (Neymar -> Brazil -> Ronaldo Cabrais -> Grêmio),
`team_graph` lists a club's competitions, most frequent opponents and
FIFA squad. This satisfies the spec's "knowledge graph interface" without
requiring an external graph database.

### Tools (19)

| Category | Tools |
|----------|-------|
| Matches | `search_matches`, `head_to_head` |
| Teams | `team_stats`, `team_profile`, `best_records` |
| Players | `search_players`, `top_players`, `players_at_brazilian_clubs` |
| Competitions | `standings`, `competition_finals`, `competition_info`, `top_scoring_teams` |
| Statistics | `goal_averages`, `biggest_wins`, `derbies` |
| Graph | `graph_overview`, `team_graph`, `graph_paths` |
| Support | `list_clubs` |

Standings are calculated from match results with CBF tie-breakers
(points, wins, goal difference, goals scored) and include a completeness
note when the dataset only partially covers a season (e.g. Série A 2023).
Cup finals resolve two-legged aggregates; level aggregates are flagged as
"decided on penalties (not recorded in data)".

### Data quality notes

- The FIFA 19 snapshot excludes some Brazilian clubs for licensing reasons
  (Flamengo, Palmeiras, Corinthians, São Paulo, Vasco have no squads in
  it); 15 Brazilian clubs are covered. Player queries for uncovered clubs
  return an explanatory note.
- Individual goal scorers are not recorded anywhere in the datasets, so
  "top scorers" questions are answered at team level with a note.
- 2022 Série A in Brasileirao_Matches.csv has 81 matches without scores;
  these are completed from BR-Football during reconciliation.

## Testing

BDD Gherkin scenarios (pytest-bdd) plus GWT-structured pytest modules:

```
tests/features/*.feature            7 feature files, 35 scenarios
tests/test_bdd_features.py          step definitions for all features
tests/test_match_queries.py         search filters, reconciliation invariants
tests/test_team_queries.py          stats, profiles, record rankings
tests/test_player_queries.py        player search and FIFA data facts
tests/test_competition_queries.py   standings/finals incl. 2019 spec example
tests/test_statistics.py            goal averages, biggest wins, derbies,
                                    performance criteria (<2s / <5s)
tests/test_knowledge_graph.py       graph structure and path finding
tests/test_normalization.py         unit tests for name/date normalization
tests/test_sample_questions.py     28 end-to-end sample questions via MCP tools
tests/test_stdio_transport.py       real JSON-RPC protocol round-trip
```

155 tests, 94% coverage of the package (`pytest --cov=soccer_mcp`).
Sample facts verified against the spec and history: the 2019 Série A table
reproduces the spec's example exactly (Flamengo 90 pts, 28W 6D 4L), and
champions for 2003-2022 match the historical record.
