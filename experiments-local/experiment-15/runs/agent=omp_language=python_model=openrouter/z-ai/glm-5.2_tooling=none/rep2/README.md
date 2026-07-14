# Books API

A small REST service for managing a book collection, written in Python
with [FastAPI](https://fastapi.tiangolo.com/) and SQLite.

## Endpoints

| Method   | Path           | Description                              | Status codes          |
| -------- | -------------- | ---------------------------------------- | --------------------- |
| `GET`    | `/health`      | Liveness probe                           | 200                   |
| `POST`   | `/books`       | Create a book (title, author, year, isbn)| 201, 422 (validation) |
| `GET`    | `/books`        | List all books; supports `?author=` filter | 200               |
| `GET`    | `/books/{id}`  | Get a single book                        | 200, 404              |
| `PUT`    | `/books/{id}`  | Replace a book                           | 200, 404, 422         |
| `DELETE` | `/books/{id}`  | Delete a book                            | 204, 404              |

### Book shape

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required and must be non-empty. `year` and
`isbn` are optional.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload --port 8000
```

Then open http://localhost:8000/docs for the interactive Swagger UI.

The SQLite database file `books.db` is created next to the app on first
run.

## Tests

```bash
pytest -v
```

Five integration tests in `test_books.py` cover the create/get/list/
update/delete lifecycle, author filtering, 404s, input validation, and
the health endpoint. Each test uses a fresh database.
