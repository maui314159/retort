# Evaluation: agent=prime language=python model=openrouter/z-ai/glm-5.2 tooling=none · rep 2

## Summary

- **Factors:** language=python, agent=prime, model=openrouter/z-ai/glm-5.2, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — from `test_coverage=0.96` (tests ran + all passed; `_score_stdout.log`: "6 passed")
- **Lint:** pass — `code_quality=0.62` from scores.json
- **Architecture:** single-module FastAPI app (`app.py`), see below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:159 create_book` — INSERT with title/author/year/isbn, 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:178 list_books` — returns BookList |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:184` — `WHERE author LIKE ?` (substring, case-insensitive) |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `app.py:197 get_book` — 404 when row None |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:209 update_book` — partial update, 404 if absent |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:240 delete_book` — 204, 404 if rowcount 0 |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:8,51 init_db` — sqlite3, `books` table |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/204 across routes; validation → 422 (see finding) |
| R9 | Validation: title/author required | ✓ implemented | `app.py:76-88` — Field(...) + `_not_blank` validator; test_input_validation |
| R10 | GET /health | ✓ implemented | `app.py:147 health_check` — checks DB connectivity |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, uvicorn run, usage, tests |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 6 tests, all pass (`test_coverage=0.96`) |

## Build & Test

Scores read from `scores.json` / `_score_stdout.log` — not re-run.

```text
pytest (scorer)
......                                                        [100%]
6 passed, 1 warning in 1.23s   # StarletteDeprecationWarning only
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 245 (app.py) + 150 (test_app.py) |
| Files | 4 (app.py, test_app.py, README.md, requirements.txt) |
| Dependencies | 4 (fastapi, uvicorn, httpx, pytest) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| test_coverage | 0.96 |
| code_quality | 0.62 |
| token_efficiency | 0.064 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] code_quality score 0.62 from scorer — minor style/complexity, not functional
2. [info] Validation rejects with 422, not 400 — FastAPI/pydantic-idiomatic, acceptable
3. [info] Low token_efficiency (0.064) — high agent verbosity for a small deliverable

## Architecture

Single-file FastAPI service. `app.py` holds: a SQLite `get_db` context manager
(commit/rollback/close), `init_db` schema creation via a `lifespan` startup hook,
pydantic models (`BookCreate` with required-non-blank validators, `BookUpdate`
partial, `Book`, `BookList`, `HealthStatus`), and six routes (health + CRUD).
Tests use `TestClient` with an autouse fixture pointing `DATABASE_PATH` at a
per-test `tmp_path` DB. No `summary/` generated (single-module app).

## Reproduce

```bash
cd experiments-local/experiment-mu-primeagent-easy/runs/agent=prime_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep2
cat scores.json _score_stdout.log        # stored build/test/lint scores
pytest -v                                # 6 pass (optional re-run)
```
