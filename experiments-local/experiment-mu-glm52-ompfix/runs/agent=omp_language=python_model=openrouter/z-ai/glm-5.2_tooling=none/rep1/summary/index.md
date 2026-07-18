# Architecture summary

> Authored inline by `evaluate-run`. The `run-summary` skill was not invoked
> (CLI auto-invocation is WIP per `skills/README.md`); this file stands in for it.

## Module graph

```
server.py        FastMCP server — 13 @mcp.tool() wrappers, stdio transport
   |             _get_engine() is @lru_cache(maxsize=1): CSVs load once per process
   v
query_engine.py  QueryEngine — one method per spec query category; every method
   |             returns a preformatted human-readable string for the LLM
   v
knowledge_graph.py  KnowledgeGraph — nodes (team/player/match/competition/season)
   |                + typed edges, and six lookup indexes built once at construction
   v                (_matches_by_team, _matches_by_competition, _matches_by_season,
   |                 _h2h, _players_by_club, _players_by_nationality)
data_loader.py   load_datasets() -> LoadedData; one loader fn per CSV schema
   |
   +-- normalize.py  TeamNormalizer — fitted on the full universe of raw team
   |                 strings (two-pass), handles "-SP" suffixes, accents, collisions
   +-- models.py     Match / Player / Team / Competition / Node / Edge dataclasses
```

## Notable design decisions

- **Two-pass loading.** `_collect_raw_team_names()` sweeps every match file *and*
  the FIFA `Club` column first, so `TeamNormalizer` is fitted on the full name
  universe before any record is built. This is what lets FIFA club names link to
  match-data team names.
- **Deliberate de-duplication across overlapping datasets.** The spec ships five
  match CSVs with overlapping coverage. `_load_novo` drops seasons >= 2012
  (overlap with `Brasileirao_Matches.csv`) and `_load_br_football` skips any
  `(competition, season)` pair already supplied by a primary source. Both are
  documented in module docstrings as protecting standings from double-counting —
  this is the single most consequential correctness decision in the run, and it
  is reasoned about explicitly rather than stumbled into.
- **Answer formatting lives in the query engine, not the server.** Each
  `QueryEngine` method returns the spec's example answer format as a string, so
  the MCP tool layer is a thin parameter-forwarding shim.
- **Graph is built but only lightly used.** Nodes/edges are constructed for all
  ~17k matches and 18k players, but queries are served from the flat indexes.
  The edge set satisfies the spec's "knowledge graph interface" framing; it is
  not on the hot path.

## Test architecture

- `tests/features/*.feature` — 19 Gherkin scenarios across the five spec query
  categories, wired by `pytest_bdd.scenarios()` in the matching `test_*.py`.
- `tests/test_mcp_server.py` — 40 conventional structural/unit tests.
- `tests/conftest.py` — session-scoped `engine` fixture loads the real CSVs once
  (~4s) and shares the `QueryEngine` across all 59 tests. Tests run against real
  data, not fixtures.
