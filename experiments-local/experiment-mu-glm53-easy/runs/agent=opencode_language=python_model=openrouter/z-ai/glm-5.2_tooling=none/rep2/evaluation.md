# Evaluation: agent=opencode language=python model=openrouter/z-ai/glm-5.2 tooling=none · rep 2

## Summary

- **Factors:** language=python, model=openrouter/z-ai/glm-5.2, agent=opencode, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective) — from test_coverage=0.92, defect_rate=1.0
- **Build:** pass (import + test gate) — not re-run (scores from scores.json)
- **Lint:** pass — code_quality=0.67 (below 1.0, non-blocking; no lint gate failure)
- **Architecture:** stdlib-only HTTP service; pure `BookAPI.dispatch` split from `BaseHTTPRequestHandler` for socket-free unit testing; SQLite persistence in `bookdb.py`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:105` POST branch → `db.insert`, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:101` → `db.list`, returns 200 |
| R3 | ?author= filter | ✓ implemented | `app.py:102` reads `author` param → `bookdb.py:56` WHERE author=? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:121` GET-by-id; `app.py:124` 404 if absent |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:126` PUT branch → `bookdb.py:72` update |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:134` DELETE branch → `bookdb.py:89`, 204 |
| R7 | SQLite persistence | ✓ implemented | `bookdb.py:32` sqlite3.connect + schema |
| R8 | JSON + correct status codes | ✓ implemented | `app.py:163` `_write` JSON; 201/200/204/400/404/500 throughout |
| R9 | title & author required | ✓ implemented | `app.py:67-71` full-create validation raises 400 |
| R10 | GET /health | ✓ implemented | `app.py:97` returns 200 `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` endpoints table + Setup/run sections |
| R12 | ≥3 tests | ✓ implemented | 18 tests (14 in test_dispatch.py, 4 in test_http.py) |

## Build & Test

```text
# not re-run — scores read from scores.json
test_coverage = 0.92   (>0 ⇒ build + all tests passed)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.6667
maintainability = 0.8704
```

18 tests collected, 0 skipped (grep for `pytest.skip|xfail` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 580 |
| Files (source + docs) | 6 |
| Dependencies | 0 (stdlib only) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| test_coverage | 0.92 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] code_quality=0.67 — missing type annotations; non-blocking
2. [info] Author filter is exact-match only (spec-compliant)
3. [info] SQLite persistence present and correct (R7 satisfied)

No critical or high findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiments-local/experiment-mu-glm53-easy/runs/agent=opencode_language=python_model=openrouter/z-ai/glm-5.2_tooling=none/rep2
cat scores.json                         # stored mechanical scores
grep -rEc "^def test_" test_*.py         # test count
grep -rEn "pytest\.skip|xfail" *.py      # skip count (0)
```
