# Book Collection REST API

A small REST API service for managing a book collection, written in Python
with [Flask](https://flask.palletsprojects.com/) and backed by an embedded
SQLite database.

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Retrieve a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint

Data is stored in a local SQLite file (`books.db` by default). All responses
are JSON and use appropriate HTTP status codes. `title` and `author` are
required fields; `year` must be an integer when provided.

## Requirements

- Python 3.9+
- Flask

## Setup

```bash
# (optional) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

The server listens on `http://0.0.0.0:5000` by default. Override host/port
and the database location with environment variables:

```bash
PORT=8000 HOST=127.0.0.1 BOOKS_DB_PATH=/tmp/books.db python app.py
```

## Example usage

```bash
# Create a book
curl -s -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List all books
curl -s http://localhost:5000/books

# Filter by author
curl -s "http://localhost:5000/books?author=George%20Orwell"

# Get a single book
curl -s http://localhost:5000/books/1

# Update a book
curl -s -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'

# Delete a book
curl -s -X DELETE http://localhost:5000/books/1
```

## Running the tests

```bash
pip install pytest
pytest -q
```

## Project layout

```
app.py              # Flask application, routes, SQLite access, validation
requirements.txt    # Python dependencies
README.md           # This file
tests/
    test_books.py   # Unit / integration tests
```
