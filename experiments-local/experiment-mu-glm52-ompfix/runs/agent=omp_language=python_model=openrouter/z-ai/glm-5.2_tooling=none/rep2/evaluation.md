# Evaluation: agent=omp · language=python · model=openrouter/z-ai/glm-5.2 · tooling=none · rep 2

> **Provenance note (read first).** This rep was a **salvaged retry** (see the
> `second-try-score-archive-mismatch` finding for the ompfix experiment). The
> harness originally archived attempt-1's (truncated) workspace while recording
> attempt-2's scores. Post-salvage the archive here is the **real 63/63-green
> workspace**, and `scores.json` (`test_coverage=0.93`) is genuine — verified by
> the `.coverage` DB, which tracks 11 real source+test files from the playpen dir
> `retort-local-j8s0t5kx/retort-2dee2c820647`. This is a **genuine PASS**, not a
> false-PASS. The 0.93 was **not** rescored/altered.

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.2, agent=omp, tooling=none
- **Status:** ok (genuine pass — salvaged archive matches recorded scores)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 63 tests / 0 failed / 0 skipped (63 effective) — from `summary/index.md`, coverage-DB confirms execution
- **Build:** pass — `test_coverage=0.93` from `scores.json` (1.0 ⇒ tests ran & passed; 0.93 is a coverage fraction, gate cleared)
- **Lint:** pass-with-warnings — `code_quality=0.6667`; 15 ruff errors (10 E501, 5 I001), all cosmetic
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py` — `FastMCP("brazilian-soccer-mcp")`, 14 `@mcp.tool` + `data://summary` resource |
| R2 | Loads bundled `data/kaggle/` datasets | ✓ implemented | `loader.py:DATA_DIR = data/kaggle`; 6 CSVs present; `test_loader.py:test_all_data_files_present` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `queries.find_matches` + `_team_mask(side=…)`; `TestFindMatchesByTeam` (4 tests) |
| R4 | Match query by date range / season | ✓ implemented | `find_matches` start_date/end_date/season; `TestFindMatchesByDateAndSeason` (3 tests) |
| R5 | Match query by competition | ✓ implemented | `_competition_filter`; `TestFindMatchesByCompetition` covers Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `team_statistics` / `_compute_record` → `TeamRecord`; `TestTeamStatistics` (4 tests) |
| R7 | Player search by name | ✓ implemented | `search_players(name=…)`, accent-insensitive; `TestSearchPlayersByName` (2 tests) |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `search_players` nationality/club/overall; `_player_row_to_dict` returns ratings+attrs; `TestSearchPlayersByFilters` (5 tests) |
| R9 | Standings computed from match results | ✓ implemented | `competition_standings` (3pts/win, GD tiebreak); `test_standings_not_hardcoded` proves derivation |
| R10 | Aggregate statistical analysis | ✓ implemented | `average_goals`, `biggest_wins`, `best_team_record`; `TestStatisticalAnalysis` (5 tests) |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` returns W/L/D per team; `TestHeadToHead` (3 tests) |
| R12 | Automated tests covering the queries | ✓ implemented | 5 test files (63 tests) + pytest-bdd feature; `test_coverage=0.93 > 0` |

## Build & Test

Not re-run — stored scores are authoritative (skill step 2).

```text
# from scores.json (salvaged, matches archive)
test_coverage = 0.93   # tests executed and passed; coverage fraction, gate cleared
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.6667
```

```text
# test inventory (summary/index.md; cross-checked against grepped test defs)
63 tests total = 10 loader + 35 queries + 11 server + 7 pytest-bdd scenarios
0 skipped, 0 xfail (grep pytest.skip/xfail => 0)
.coverage DB tracks 11 real files => archive == executed workspace
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,467 (cloc: brazilian_soccer + tests) |
| Files (`.py`, excl. caches) | 11 |
| Dependencies | fastmcp, pandas, pytest-bdd (pyproject.toml) |
| Tests total | 63 |
| Tests effective | 63 |
| Skip ratio | 0% |
| Lint errors | 15 (10 E501, 5 I001 — cosmetic) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] 10 E501 line-too-long lint errors in source
2. [low] 5 I001 unsorted-import blocks (tests)
3. [info] Cross-source match deduplication beyond spec (`loader.py`)
4. [info] 14 MCP tools + derby/relegation/champion helpers exceed the 11 required queries
5. [info] Server layer is a pure pass-through with no input validation

No requirement gaps, no skipped tests, no build/test failures.

## Reproduce

```bash
cd "experiments-local/experiment-mu-glm52-ompfix/runs/agent=omp_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep2"
cat scores.json                                            # authoritative stored scores
python3 -c "import sqlite3;print([r[0] for r in sqlite3.connect('.coverage').execute('select path from file')])"  # 11 real files => salvaged good archive
grep -rE 'pytest\.skip|@pytest\.mark\.skip|xfail' tests/   # 0 skips
ruff check brazilian_soccer tests --output-format=concise  # 15 cosmetic errors
```
