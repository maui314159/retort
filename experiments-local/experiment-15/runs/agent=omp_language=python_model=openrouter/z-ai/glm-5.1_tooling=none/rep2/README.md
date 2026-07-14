# Book Collection REST API

A simple REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Setup

```bash
pip install fastapi uvicorn pydantic
```

## Run the server

```bash
uvicorn app:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

### Book fields

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| title | yes | string | Must be non-empty |
| author | yes | string | Must be non-empty |
| year | no | integer | |
| isbn | no | string | |

## Run tests

```bash
pip install pytest httpx
pytest test_app.py -v
```
