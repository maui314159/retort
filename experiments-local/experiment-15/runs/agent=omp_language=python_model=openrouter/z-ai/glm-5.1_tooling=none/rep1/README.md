# Book Collection API

A REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx pytest pytest-anyio
```

## Run the server

```bash
uvicorn app:app --reload
```

The API is available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

## Endpoints

| Method   | Path          | Description              |
|----------|---------------|--------------------------|
| GET      | /health       | Health check             |
| POST     | /books        | Create a new book        |
| GET      | /books        | List all books           |
| GET      | /books/{id}   | Get a book by ID         |
| PUT      | /books/{id}   | Update a book            |
| DELETE   | /books/{id}   | Delete a book            |

### Query parameters

- `GET /books?author=<name>` — filter books by author

### Request body (POST /books)

```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": 2024,
  "isbn": "string"
}
```

### Request body (PUT /books/{id})

All fields optional; only provided fields are updated.

```json
{
  "title": "string",
  "author": "string",
  "year": 2024,
  "isbn": "string"
}
```

## Run tests

```bash
pytest -v
```
