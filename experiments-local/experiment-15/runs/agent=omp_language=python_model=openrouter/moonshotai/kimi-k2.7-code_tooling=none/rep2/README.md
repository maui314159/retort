# Book Collection API

A REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, list, retrieve, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint

## Setup

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

Start the server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

| Method | Endpoint       | Description                  |
|--------|----------------|------------------------------|
| GET    | /health        | Health check                 |
| POST   | /books         | Create a new book            |
| GET    | /books         | List books (filter: ?author=)|
| GET    | /books/{id}    | Get a book by ID             |
| PUT    | /books/{id}    | Update a book                |
| DELETE | /books/{id}    | Delete a book                |

## Example

```bash
curl -X POST "http://127.0.0.1:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
```

## Run Tests

```bash
pytest
```
