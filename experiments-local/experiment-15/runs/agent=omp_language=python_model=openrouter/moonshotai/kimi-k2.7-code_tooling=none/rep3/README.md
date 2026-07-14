# Book Collection API

A REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation for required fields
- Health check endpoint

## Requirements

- Python 3.10+

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

| Method | Endpoint         | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/health`        | Health check                         |
| POST   | `/books`         | Create a new book                    |
| GET    | `/books`         | List all books (optional `?author=`) |
| GET    | `/books/{id}`    | Get a single book by ID              |
| PUT    | `/books/{id}`    | Update a book                        |
| DELETE | `/books/{id}`    | Delete a book                        |

## Example Usage

Create a book:

```bash
curl -X POST "http://127.0.0.1:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'
```

List books by author:

```bash
curl "http://127.0.0.1:8000/books?author=Tolkien"
```

## Tests

Run the test suite with pytest:

```bash
pytest
```
