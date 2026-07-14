# Book Collection API

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features
- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite embedded database storage

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## API Endpoints

- `GET /health` - Health check
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` query parameter for filtering)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Testing

Run the test suite using pytest:
```bash
pytest test_main.py -v
```
