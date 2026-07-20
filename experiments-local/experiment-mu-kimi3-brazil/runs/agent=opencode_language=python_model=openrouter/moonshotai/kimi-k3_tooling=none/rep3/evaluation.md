# Evaluation: agent=opencode_language=python_model=openrouter/moonshotai/kimi-k3_tooling=none · rep 3

## Summary

- **Factors:** language=python, model=openrouter/moonshotai/kimi-k3, tooling=none, agent=opencode
- **Status:** ok (`_meta.json`: succeeded=true)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator 12)
- **Tests:** 34 passed / 0 failed / 0 skipped (34 effective) — pytest-bdd, 34 Gherkin scenarios
- **Build:** pass — from stored scores (`scores.json`: test_coverage=0.91, defect_rate=0.987); not re-run
- **Lint:** pass with warnings — code_quality=0.80 from stored scores
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

Pinned checklist from `experiment-mu-kimi3-brazil/REQUIREMENTS.json` (used verbatim). No `prompt` factor in `stack.json`, so no P* requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `server.py:24` FastMCP("brazilian-soccer"); 13 `@mcp.tool()` registrations; stdio via `mcp.run()` (`server.py:219`) |
| R2 | Uses provided data/kaggle datasets | ✓ implemented | `soccer_data.py:32` DATA_DIR=data/kaggle; all 6 CSVs loaded in `get_store()` (`soccer_data.py:412-425`) |
| R3 | Matches by team (home/away/either) | ✓ implemented | `query_engine.py:180-187` team filter with venue=home/away/either; `tests/features/match_queries.feature` |
| R4 | Filter by date range / season | ✓ implemented | `query_engine.py:165-170` season + date_from/date_to; tested (search by season and by date range steps, `tests/test_match_queries.py:20-38`) |
| R5 | Filter by competition | ✓ implemented | `query_engine.py:44-59` alias table → canonical names incl. Brasileirão A/B/C, Copa do Brasil, Libertadores; `_filter_matches` (`query_engine.py:162-164`) |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `query_engine.py:263-310` `_record_for` + `team_statistics`; `tests/features/team_queries.feature` (4 scenarios) |
| R7 | Player search by name | ✓ implemented | `query_engine.py:357-359` name_key contains-match; `tests/features/player_queries.feature` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `query_engine.py:360-365` nationality/club filters; `_player_to_dict` returns Overall/Potential (`query_engine.py:329-345`) |
| R9 | Season standings computed from matches | ✓ implemented | `query_engine.py:452-495` points 3/1/0 + tie-breaks, computed not hardcoded; `tests/features/competition_queries.feature` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `query_engine.py:603-627` `competition_overview`; `query_engine.py:539-557` `biggest_wins`; `tests/features/statistics.feature` (6 scenarios) |
| R11 | Head-to-head between two teams | ✓ implemented | `query_engine.py:225-257` `head_to_head` with per-team wins + draws; H2H scenario in `match_queries.feature` |
| R12 | Automated tests covering queries | ✓ implemented | 34 pytest-bdd scenarios, all pass ("34 passed in 11.75s", `_agent_stdout.log`); coverage 0.91 (`scores.json`) |

Beyond spec: extra tools (`player_profile`, `top_players`, `best_team_records`, `list_competitions`, `top_scoring_teams`), ~100-entry team-alias normalisation with state-suffix disambiguation, and cross-source fixture de-duplication (`soccer_data.py:277-292`) — surfaced in `summary/index.md`, not scored.

## Build & Test

Not re-run — stored scores used per skill Step 2.

```text
scores.json (written by the runner at scoring time):
  test_coverage      = 0.91   (tests executed; build+import OK)
  code_quality       = 0.80
  defect_rate        = 0.987
  maintainability    = 0.578
  token_efficiency   = 0.0077
```

```text
Final agent-log test run (_agent_stdout.log):
  34 passed in 11.75s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Python, incl. tests) | 1387 |
| — source only (server/query_engine/soccer_data) | 1275 raw lines |
| Files (excl. data/, logs, __pycache__) | 27 |
| Dependencies (requirements.txt) | 4 (pandas, mcp, pytest, pytest-bdd) |
| Tests total | 34 |
| Tests effective | 34 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] code_quality scored 0.80 — residual lint findings (`scores.json`)
2. [low] `_display_names` rebuilt on every `_team_name` call — repeated groupby per serialised row (`query_engine.py:124-125`)
3. [info] MCP tool layer (`server.py`) not directly exercised by tests — R1 verified structurally

## Reproduce

```bash
cd experiments-local/experiment-mu-kimi3-brazil/runs/agent=opencode_language=python_model=openrouter/moonshotai/kimi-k3_tooling=none/rep3
cat scores.json _meta.json stack.json
grep -Eo "[0-9]+ passed[^\"]*" _agent_stdout.log | tail -3
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
grep -c "Scenario:" tests/features/*.feature
cloc . --exclude-dir=node_modules,target,__pycache__,.git,dist,build,data
```
