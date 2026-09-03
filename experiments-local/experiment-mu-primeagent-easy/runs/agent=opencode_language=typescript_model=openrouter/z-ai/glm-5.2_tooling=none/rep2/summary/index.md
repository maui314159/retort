# Architecture summary

Small, cleanly layered Express + SQLite REST service (TypeScript, ESM).

- **src/db.ts** — `BookStore` class wrapping `better-sqlite3`. Owns the schema
  (`books` table, autoincrement id, created_at/updated_at), and exposes
  `listAll(authorFilter?)`, `getById`, `create`, `update`, `delete`, `close`.
  Default path `:memory:`; `index.ts` passes a file path for real persistence.
- **src/validation.ts** — pure `validateBook(input): ValidationResult` discriminated
  union. Enforces non-empty title/author, optional integer year (0..currentYear+1),
  optional isbn; trims strings. No I/O — unit-testable in isolation.
- **src/app.ts** — `createApp({store})` builds the Express app with all six routes
  plus `/health` and a JSON-error/500 fallback middleware. Dependency-injects the
  store, so tests mount an in-memory store.
- **src/index.ts** — composition root: builds store from `DB_PATH`, starts the
  listener on `PORT`, wires SIGINT/SIGTERM graceful shutdown.

Flow: request → express.json() → route handler → validateBook (writes) → BookStore
→ JSON response. Clean separation of transport (app), domain validation
(validation), and persistence (db).
