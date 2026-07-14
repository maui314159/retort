# Book Collection API

A small REST service for managing a book collection, built with **FastAPI**
and **SQLite**.

## Endpoints

| Method | Path             | Description                                          |
| ------ | ---------------- | ---------------------------------------------------- |
| GET    | `/health`        | Liveness probe (also checks DB reachability)         |
| POST   | `/books`         | Create a book (`title`, `author` required)           |
| GET    | `/books`         | List books; `?author=` filter (case-insensitive)     |
| GET    | `/books/{id}`    | Fetch a single book                                  |
| PUT    | `/books/{id}`    | Update a book (partial — only fields sent are saved) |
| DELETE | `/books/{id}`    | Remove a book                                        |

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "9780201616224"
}
```

`title` and `author` are required and must be non-blank. `year` (0–2100)
and `isbn` (≤32 chars) are optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

The API will be available at <http://127.0.0.1:8000>; interactive docs at
<http://127.0.0.1:8000/docs>.

The SQLite file defaults to `./books.db`; override with the
`BOOKS_DB_PATH` environment variable.

## Test

```bash
pytest -v
```

Each test session uses a fresh temporary SQLite file, so tests are
isolated from any local `books.db` and from each other.

## Example session

```bash
curl -X POST http://127.0.0.1:8000/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
     -H 'Content-Type: application/json' -d '{"year":1966}'
curl -X DELETE http://127.0.0.1:8000/books/1 -i
```
