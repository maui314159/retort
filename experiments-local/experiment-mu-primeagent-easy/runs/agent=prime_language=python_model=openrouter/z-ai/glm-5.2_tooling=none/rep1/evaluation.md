# Evaluation: agent=prime language=python model=openrouter/z-ai/glm-5.2 tooling=none · rep 1

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.2, agent=prime, tooling=none, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — tests import and run (test_coverage=0.93 from scores.json)
- **Lint:** pass with warnings — code_quality=0.62 from scores.json (not re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:128 create_book`, INSERT at :139, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:149 list_books`, SELECT ... ORDER BY id :158 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:151-156` WHERE author = ?; test `test_list_books_with_author_filter` |
| R4 | GET /books/{id} single (404 absent) | ✓ implemented | `app.py:162 get_book`, 404 at :167; `test_get_nonexistent_book_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:171 update_book`, partial merge :186-191, 404 at :184 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:201 delete_book`, DELETE :207, 404 at :205 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8 import sqlite3`; `init_db` CREATE TABLE books :44 |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:76-80 validate_book`; `test_create_requires_title_and_author` |
| R10 | GET /health | ✓ implemented | `app.py:123 health` → `{"status":"ok"}`, 200; `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup + Run + Tests sections |
| R12 | ≥3 tests | ✓ implemented | 7 tests in `test_app.py`; 7 passed (scores.json) |

## Build & Test

Scores read from `scores.json` / `_sandbox_meta.json` — not re-run (per skill).

```text
# pytest (recorded in _score_stdout.log)
.......                                                                  [100%]
7 passed in 0.44s
```

```text
test_coverage=0.93  (coverage_pct=92.74, tests_passed=7/7)   — scores.json / _sandbox_meta.json
code_quality=0.62   defect_rate=0.83   maintainability=0.90  — scores.json
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 303 (app.py 217, test_app.py 86) |
| Files | 12 (incl. app, tests, README, requirements, artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Coverage | 92.74% |
| Agent time | 70s (agent_exit=0) |

## Findings

Top findings (full list in `findings.jsonl`) — no high/critical/medium/low findings:

1. [info] PUT /books/{id} implements partial update (field merge) — exceeds spec
2. [info] Input validation exceeds spec (year non-negative int, isbn type, empty-string rejection)

## Reproduce

```bash
cd "experiments-local/experiment-mu-primeagent-easy/runs/agent=prime_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep1"
cat scores.json _sandbox_meta.json      # stored mechanical scores (not re-run)
python -m pytest -v                      # 7 passed (optional re-verify)
```
