# Evaluation: agent=opencode_language=python_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 1

## Summary

- **Factors:** language=python, model=openrouter/moonshotai/kimi-k3, agent=opencode, tooling=none (no `prompt` factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, constant denominator 12)
- **Tests:** 117 passed / 0 failed / 0 skipped (117 effective)
- **Build:** pass — from stored scores (`defect_rate=1.0`, `test_coverage=0.97` in `scores.json`; matches retort.db run id 11); not re-run
- **Lint:** pass with warnings — `code_quality=0.67` from stored scores
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

Pinned checklist from `experiment-mu-kimi3-brazil/REQUIREMENTS.json` (used verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `brazilian_soccer_mcp/server.py:19` FastMCP app, 11 `@mcp.tool()` registrations; `tests/test_server.py` |
| R2 | Uses provided data/kaggle CSVs | ✓ implemented | `brazilian_soccer_mcp/data.py` — 6 `pd.read_csv` loaders (lines 130–231), one per bundled CSV; no external API |
| R3 | Matches by team (home/away/either) | ✓ implemented | `queries.py:find_matches` (`home_key`/`away_key` filter, line 168); `tests/test_queries.py`, `tests/features/matches.feature` |
| R4 | Filter by date range and/or season | ✓ implemented | `queries.py:_filter_matches` (season eq, date_from/date_to, lines 129–140); multi-format dates via `normalization.parse_date` |
| R5 | Filter by competition | ✓ implemented | `queries.py:_competition_mask` (line 90), accent-insensitive across Brasileirão/Copa do Brasil/Libertadores labels set in `data.py:27-31` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `queries.py:team_stats` (line 233) — wins/draws/losses, goals_for/against, venue + per-competition breakdown |
| R7 | Player search by name | ✓ implemented | `queries.py:search_players` name filter (line 388); "Who is Neymar" sample-question OK in `_agent_stdout.log` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `queries.py:search_players` nationality/club/position/min_overall filters; `_player_to_dict` returns Overall/Potential |
| R9 | Standings computed from matches | ✓ implemented | `queries.py:standings` (line 290) — 3/1/0 points loop over match rows, Brazilian tie-break, champion/relegation flags |
| R10 | Aggregate statistics | ✓ implemented | `queries.py:competition_stats` (avg goals, home/away win rates) and `biggest_wins` (line 444) |
| R11 | Head-to-head between two teams | ✓ implemented | `queries.py:head_to_head` (line 180) — wins_a/wins_b/draws/goals; H2H sample question OK |
| R12 | Automated tests covering the queries | ✓ implemented | 117 tests pass (`_agent_stdout.log`: "117 passed in 1.89s"); unit suites + 5 BDD features bound via `pytest_bdd.scenarios()`; stored `test_coverage=0.97` |

No `prompt` factor was set (`stack.json` has none), so there are no P* requirements.

**Beyond spec:** `list_teams`, `list_competitions`, `dataset_summary` tools; `resolve_team` did-you-mean suggestions; env-overridable data dir.

## Build & Test

Not re-run (per skill: stored scores exist). Stored evidence:

```text
scores.json: {"code_quality": 0.667, "test_coverage": 0.97, "defect_rate": 1.0,
              "maintainability": 0.677, "token_efficiency": 0.0085}
retort.db run id 11 (completed, replicate 1) carries identical metrics,
plus _duration_seconds=2491, _tokens=4771834, _cost_usd=2.997
```

```text
_agent_stdout.log (agent's final verification):
117 passed in 1.89s
sample questions sweep: 15/15 OK (Fla-Flu, Corinthians home 2022,
2019 champion, 2020 relegation, Neymar, top Brazilians, biggest wins, ...)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Python, source+tests) | 1,891 |
| Files (excl. data/, caches) | 34 |
| Dependencies | mcp, pandas (+ pytest, pytest-bdd, pytest-cov, ruff dev) per `pyproject.toml` |
| Tests total | 117 |
| Tests effective | 117 |
| Skip ratio | 0% |
| Run duration / cost | 2491 s · 4.77 M tokens · $3.00 (retort.db) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] code_quality scored 0.67 — residual lint warnings (scores.json)
2. [info] Coverage 97%, not 100%
3. [info] Console-script stdio smoke logged a benign JSONRPC EOF (server starts; all sample queries answered)
4. [info] Enhancement beyond spec (extra tools, name-suggestion UX)

## Reproduce

```bash
cd experiments-local/experiment-mu-kimi3-brazil/runs/agent=opencode_language=python_model=openrouter/moonshotai/kimi-k3_tooling=none/rep1
cat scores.json stack.json _meta.json
sqlite3 -readonly ../../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id=11;"
grep -oE "[0-9]+ passed[^\"]*" _agent_stdout.log | tail -3
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
cloc . --exclude-dir=node_modules,__pycache__,.git,data,brazilian_soccer_mcp.egg-info
```
