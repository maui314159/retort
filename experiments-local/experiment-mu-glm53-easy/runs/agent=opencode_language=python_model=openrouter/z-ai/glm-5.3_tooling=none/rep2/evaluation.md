# Evaluation: agent=opencode language=python model=openrouter/z-ai/glm-5.3 tooling=none · rep 2

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.3, agent=opencode, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all pass / 0 failed / 0 skipped (19 test functions, several parametrized; ~40+ effective cases)
- **Build:** pass (import + tests ran) — from `test_coverage=0.97` in scores.json
- **Lint:** 6 ruff warnings (import order + line length) — `code_quality=0.62`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:146 create_book` — INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:133 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:135-141` LIKE w/ escaped wildcards |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:164 get_book`, 404 at :170 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:173 update_book` (partial updates) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:195 delete_book`, 204/404 |
| R7 | Stored in SQLite | ✓ implemented | `app.py:19,24-34,51-57` sqlite3 + schema |
| R8 | JSON responses + status codes | ✓ implemented | jsonify + 201/200/404/400/204 throughout |
| R9 | title & author required | ✓ implemented | `app.py:72-90 validate_payload` (creating) |
| R10 | GET /health | ✓ implemented | `app.py:129-131` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` (103 lines, setup+run+endpoints) |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` 19 test fns, `test_coverage=0.97` |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.97   -> build + tests executed and passed
defect_rate   = 1.0    -> build+test succeeded
code_quality  = 0.622  -> lint (6 ruff findings)
maintainability = 1.0
```

Skip scan: `grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_app.py` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 209 |
| Test LoC (test_app.py) | 159 |
| README LoC | 103 |
| Dependencies | 2 (flask, pytest) |
| Test functions | 19 (parametrized → 40+ cases) |
| Skipped tests | 0 |
| Skip ratio | 0% |
| Coverage | 97% |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [low] 6 ruff violations — import order (I001) + line-too-long (E501); 1 autofixable
2. [info] Author filter is partial + case-insensitive with escaped LIKE wildcards (beyond spec)
3. [info] created_at/updated_at columns + JSON error handlers beyond spec

No critical, high, or medium findings. All 12 pinned requirements implemented and tested.

## Reproduce

```bash
cd experiments-local/experiment-mu-glm53-easy/runs/agent=opencode_language=python_model=openrouter/z-ai/glm-5.3_tooling=none/rep2
cat scores.json                       # stored mechanical scores
grep -Ec "pytest.skip|xfail" test_app.py
ruff check app.py test_app.py         # lint signal behind code_quality
```
