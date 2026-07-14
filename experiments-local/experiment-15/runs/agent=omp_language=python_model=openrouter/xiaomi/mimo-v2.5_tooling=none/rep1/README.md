# Book Collection REST API

A FastAPI service for managing a book collection with SQLite storage.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List books (optional `?author=` filter) |
| GET | /books/{id} | Get a book |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

## Tests

```bash
pytest tests.py -v
```
