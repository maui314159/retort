# Architecture summary

Single-module Flask service (`app.py`, 217 LoC) backed by SQLite.

## Modules

- **`app.py`** — the entire service.
  - *DB helpers*: `get_db()` (request-scoped `sqlite3.Row` connection), `close_db()` (teardown), `init_db(db_path)` (idempotent `CREATE TABLE IF NOT EXISTS books`). DB path from `BOOKS_DB_PATH` env var (default `books.db`), overridable for tests.
  - *Validation*: `validate_book(data, partial=False)` returns `(payload, errors)`; enforces required `title`/`author` on create, non-empty on update, `year` non-negative int, `isbn` str. `row_to_book(row)` serializes.
  - *Routes*: `/health` (GET), `/books` (POST create, GET list with `?author=`), `/books/<int:id>` (GET/PUT/DELETE). PUT does a partial merge over the existing row.
- **`test_app.py`** — 7 pytest tests using a `tmp_path`-backed DB fixture and Flask test client.

## Interfaces / flow

Request → Flask route → `validate_book` (on writes) → `get_db()` parametrized SQL → `jsonify(...)` with explicit status codes (201/200/400/404). Connections are per-request via Flask `g` and closed on teardown.

## Notes

- Parametrized SQL throughout (no injection surface on the tested paths).
- `id` is `INTEGER PRIMARY KEY AUTOINCREMENT`; routes use `<int:book_id>` converter.
