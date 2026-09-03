# Evaluation: agent=prime language=typescript model=openrouter/z-ai/glm-5.2 tooling=none · rep 3

## Summary

- **Factors:** language=typescript, model=openrouter/z-ai/glm-5.2, agent=prime, tooling=none
- **Task:** rest-api-crud (REPAIR variant — fix an existing failed attempt)
- **Status:** ok — build + all tests pass (test_coverage=1.0 from scores.json)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 passed / 0 failed / 0 skipped (23 effective)
- **Build:** pass — tsc exits 0 (agent-verified; `_sandbox_meta.json` agent_exit=0)
- **Lint:** n/a — code_quality=0.73 (scores.json), maintainability=0.60
- **Architecture:** clean layering — types / validation / db (BookStore) / app (Express routes) / server entrypoint
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:44` POST /books → `books.create`; test "creates a book and returns 201" |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:54` GET /books → `books.list`; test "lists all books" |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:55` reads `req.query.author`; `src/db.ts:60` `WHERE author LIKE ?`; test "filters by author" |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `src/app.ts:61-72` returns 404 when missing; tests found/not-found |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:75` PUT → `books.update`; test "updates an existing book" |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.ts:96` DELETE → `books.delete`, 204; test "deletes a book and returns 204" |
| R7 | SQLite / embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` DatabaseSync, real table + prepared statements |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/400/404/204 across `src/app.ts`; verified by tests |
| R9 | Validation: title & author required | ✓ implemented | `src/validation.ts:22-38`; tests for missing title, missing author, empty strings |
| R10 | GET /health | ✓ implemented | `src/app.ts:39` returns `{status:"ok"}`; test "returns 200 and status ok" |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup, Running, Testing, env vars, examples |
| R12 | >= 3 tests | ✓ implemented | 23 `it()` cases in `src/__tests__/books.test.ts`; test_coverage=1.0 |

## Build & Test

```text
npm run build   # tsc — exits 0 (dist/ produced)
npm test        # vitest run — 23 tests, all passing (1 file)
```

Scores read from `scores.json` (inline gate) — no re-run performed:

```text
test_coverage = 1.0    (build + all tests passed)
defect_rate   = 1.0
code_quality  = 0.733
maintainability = 0.602
token_efficiency = 0.070
```

Note: the previous attempt failed only on a corrupted `node_modules` / stale
`package-lock.json` (vitest could not load `@vitest/runner`). The prime agent
fixed it with a clean reinstall; no source changes were needed. This aligns
with the known "TS node:sqlite" gate risk — here the gate passed cleanly.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (TypeScript, source only) | 472 |
| Files (src) | 6 |
| Dependencies (prod + dev) | 8 |
| Tests total | 23 |
| Tests effective | 23 |
| Skip ratio | 0% |
| Agent wall time | 140.2s (`_sandbox_meta.json`) |

## Findings

No correctness, requirement, or test-integrity findings. 2 informational notes only (full list in `findings.jsonl`):

1. [info] node:sqlite requires Node >=22.5 and is experimental (portability note; embedded-DB requirement satisfied)
2. [info] Validation leniently accepts numeric-string year (documented, tested)

## Reproduce

```bash
cd "experiments-local/experiment-mu-primeagent-easy/runs/agent=prime_language=typescript_model=openrouter/z-ai/glm-5.2_tooling=none/rep3"
cat scores.json          # test_coverage=1.0 — build+tests passed (no re-run)
npm install --cache .npm-cache
npm run build            # tsc
npm test                 # vitest run — 23 tests
```

_run-summary skill not invoked (aggregation kept lightweight; architecture summarized inline above)._
