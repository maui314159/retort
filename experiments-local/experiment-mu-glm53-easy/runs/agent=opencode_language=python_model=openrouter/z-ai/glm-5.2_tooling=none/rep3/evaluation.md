# Evaluation: agent=opencode language=python model=openrouter/z-ai/glm-5.2 tooling=none · rep 3

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.2, agent=opencode, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (test_coverage=0.95 from scores.json — build+tests ran)
- **Lint:** pass — code_quality=0.789 from scores.json
- **Architecture:** single-module Flask app factory (`app.py`) + pytest suite (`test_app.py`); `run-summary` skill not invoked (not available this session)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:48` create_book; INSERT at `:57`; 201 at `:63` |
| R2 | GET /books lists all | ✓ implemented | `app.py:67` list_books; `:78` SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:69-76` filters by author query param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:83` get_book; 404 at `:89` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:94` update_book; partial update `:108-119`; 404 `:106` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:123` delete_book; 204 at `:131`; 404 `:128` |
| R7 | SQLite persistence | ✓ implemented | `app.py:12` sqlite3.connect; `init_db` `:18` |
| R8 | JSON + HTTP status codes | ✓ implemented | jsonify throughout; 201/200/400/404/204/405 |
| R9 | Validation: title+author required | ✓ implemented | `app.py:146` validate_book; 400 at `:53` |
| R10 | GET /health | ✓ implemented | `app.py:44` health → {"status":"ok"},200 |
| R11 | README setup+run | ✓ implemented | `README.md` — setup, run, env vars, endpoints |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 5 test functions, all pass |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.95   # build + tests ran and passed
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.789
maintainability = 0.976
```

Tests (`test_app.py`): 5 functions — create/get/delete lifecycle, validation, partial-update+404, author filter, health. 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 183 (app.py) |
| Test LOC | 95 (test_app.py) |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 1 (flask) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Top items (full list in `findings.jsonl`) — none at medium or above:

1. [low] New SQLite connection per request without pooling — acceptable for scope
2. [info] 405 handler returns JSON error contract (beyond spec)
3. [info] Partial-update validation supported for PUT

## Reproduce

```bash
cd experiments-local/experiment-mu-glm53-easy/runs/agent=opencode_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep3
cat scores.json          # stored mechanical scores
python -m pytest -q      # 5 passed (needs flask)
```
