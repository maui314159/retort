# Book Collection API

A simple REST API service for managing a book collection, built with Python and FastAPI, backed by SQLite.

## Endpoints

- `GET /health` — Health check
- `POST /books` — Create a new book
- `GET /books` — List all books, optionally filter with `?author=<author>`
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book

## Setup

1. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Run tests

```bash
pytest
```
