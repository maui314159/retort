# Evaluation: agent=opencode language=python model=openrouter/z-ai/glm-5.2 tooling=none · rep 1

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.2, agent=opencode, tooling=none, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 8 test functions passed / 0 failed / 0 skipped (8 effective) — `test_coverage=0.94` from retort.db (completed)
- **Build:** pass (import + tests executed; test_coverage>0) — no rebuild performed
- **Lint:** pass — `code_quality=0.62` from retort.db
- **Architecture:** single-module Flask app factory (`create_app`) + SQLite; see files below (run-summary skipped, see Notes)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:153 create_book`, INSERT at `app.py:161`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:169 list_books`, `SELECT * ... ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:171-176` filters on author query param; tested `test_app.py:45` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:181 get_book`, 404 at `app.py:186`; tested `test_app.py:70` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:189 update_book`, partial merge `app.py:201`; tested `test_app.py:58` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:215 delete_book`, returns 204; tested `test_app.py:63` |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3` schema `app.py:69-79`, persistent file via `BOOKS_DB_PATH` |
| R8 | JSON responses + correct HTTP codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 present |
| R9 | Validation: title and author required | ✓ implemented | `app.py:98 validate_book_payload` (partial=False); tested `test_app.py:27` |
| R10 | GET /health health check | ✓ implemented | `app.py:149 health` → `{"status":"ok"}` 200; tested `test_app.py:21` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, Flask CLI, env vars, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 test functions, `test_coverage=0.94` |

## Build & Test

Scores read from `retort.db` (status=completed) — no re-run per skill guidance.

```text
test_coverage = 0.94   (tests executed and passed; coverage 94%)
code_quality  = 0.62
defect_rate   = 0.922
maintainability = 0.916
duration = 230.9s, tokens = 1,922,748, cost = $0.607
```

Skips: 0 (`grep pytest.skip|xfail test_app.py` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 325 (app.py 229 + test_app.py 96) |
| Files (excl. artifacts) | 9 |
| Dependencies | 1 (flask>=3.0) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | 230.9s (run wall-clock) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] App binds to 0.0.0.0 by default — `app.py:229` (acceptable for dev/task service)
2. [info] Test suite exceeds the 3-test minimum with full CRUD lifecycle + 404/validation edge cases

No requirement, build, test, or lint failures. This is a clean pass.

## Notes

- `run-summary` skill not invoked — single 229-line module, architecture inlined above.
- Implementation quality is high: application-factory pattern, `:memory:` shared-cache handling for test isolation (`app.py:20-25`), partial-update merge semantics, and integer coercion for `year`.

## Reproduce

```bash
cd experiments-local/experiment-mu-glm53-easy/runs/agent=opencode_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep1
sqlite3 -readonly ../../../../retort.db \
  "SELECT rr.metric_name, rr.value FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id \
   WHERE json_extract(er.run_config_json,'\$.model')='openrouter/z-ai/glm-5.2' AND er.replicate=1;"
# Optional independent re-test:
# python -m pytest -v
```
