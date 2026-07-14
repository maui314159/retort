# Book Collection REST API

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features
- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite database for persistent storage

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API Endpoints

- `GET /health` - Health check
- `POST /books` - Create a new book (requires `title`, `author`; optional `year`, `isbn`)
- `GET /books` - List all books (supports `?author=` query parameter for filtering)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book (partial updates supported)
- `DELETE /books/{id}` - Delete a book

## Testing

Run the tests using pytest:
```bash
pytest test_main.py -v
```