# Book Collection REST API

A simple REST API service for managing a book collection, built with FastAPI and SQLite.

## Requirements

- Python 3.8+
- `pip`

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` query parameter for filtering)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Book Schema

- `title` (string, required): Book title
- `author` (string, required): Author name
- `year` (integer, optional): Publication year
- `isbn` (string, optional): ISBN number

## Testing

Run the test suite using pytest:

```bash
pytest test_main.py -v
```