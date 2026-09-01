# Architecture summary

Single-module Flask application factory (`app.py`, 209 LoC) backed by SQLite.

## Modules

- **`app.py`** — the whole service.
  - `create_app(db_path=None)` — application factory; initialises the DB schema,
    registers routes and error handlers. DB path from arg or `BOOKS_DB` env,
    default `books.db`.
  - Persistence helpers: `get_db` (per-request `g`-scoped connection with
    `Row` factory), `close_db` (teardown), `init_db` (idempotent `CREATE TABLE
    IF NOT EXISTS`), `book_to_dict` (row → JSON dict).
  - `validate_payload(data, *, creating)` — shared validation for create/update;
    title & author required on create, per-field checks on update.
  - Routes: `GET /health`, `GET /books` (+`?author=` partial/case-insensitive
    LIKE with escaped wildcards), `POST /books`, `GET /books/<int:id>`,
    `PUT /books/<int:id>` (partial updates), `DELETE /books/<int:id>`.
  - Error handlers convert `HTTPException` and unexpected errors to JSON.
- **`test_app.py`** — 19 test functions across 6 classes (many parametrized),
  using a `tmp_path` SQLite fixture and Flask `test_client`.

## Data flow

Request → route handler → `get_db()` (SQLite connection on `g`) →
parametrized SQL → `book_to_dict` → `jsonify`. Connection closed on app-context
teardown.

## Notable design choices

- SQL injection–safe: parametrized queries throughout; `?author=` LIKE escapes
  `\ % _`.
- `year` validation rejects bools and out-of-range values (0–9999).
- Books table carries `created_at`/`updated_at` timestamps beyond the spec.
