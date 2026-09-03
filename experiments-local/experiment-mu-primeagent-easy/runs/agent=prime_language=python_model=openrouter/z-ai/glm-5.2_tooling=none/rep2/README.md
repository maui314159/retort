# Book Collection REST API

A small REST API service for managing a book collection, built with **Python**,
**FastAPI**, and **SQLite**.

## Features

- **POST /books** — Create a new book (`title`, `author`, `year`, `isbn`)
- **GET /books** — List all books (supports `?author=` filtering)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book (partial updates supported)
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint (verifies DB connectivity)

## Tech stack

| Concern        | Choice           |
|----------------|------------------|
| Language       | Python 3.10+     |
| Web framework  | FastAPI          |
| Database       | SQLite (embedded)|
| Validation     | Pydantic         |
| Test client    | FastAPI TestClient + pytest |

## Setup

### 1. Install dependencies

```bash
pip install fastapi uvicorn httpx pytest
```

(`httpx` is required by FastAPI's `TestClient`; `pytest` for the tests.)

### 2. Run the server

From the workspace directory:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive API docs (Swagger UI) are served at `http://localhost:8000/docs`.

The SQLite database file `books.db` is created automatically in the working
directory on first run.

## Usage examples

Create a book:

```bash
curl -X POST http://localhost:8000/books   -H "Content-Type: application/json"   -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}'
```

List all books:

```bash
curl http://localhost:8000/books
```

Filter by author (case-insensitive substring):

```bash
curl "http://localhost:8000/books?author=martin"
```

Get / update / delete a book:

```bash
curl http://localhost:8000/books/1
curl -X PUT http://localhost:8000/books/1 -H "Content-Type: application/json" -d '{"year":2009}'
curl -X DELETE http://localhost:8000/books/1
```

Health check:

```bash
curl http://localhost:8000/health
```

## Validation rules

- `title` and `author` are **required** and must not be blank/whitespace-only.
- `year`, if provided, must be an integer between 0 and 9999.
- `isbn` is optional and free-form text.
- Invalid input returns HTTP `422 Unprocessable Entity`.
- Operations on a non-existent book return HTTP `404 Not Found`.

## Running tests

```bash
pytest -v
```

The test suite covers:
- Health check endpoint
- Full CRUD lifecycle (create, list, get, update, delete)
- `?author=` filtering
- Input validation (missing/blank fields, invalid year)
- 404 handling for missing books
- SQLite persistence verification
