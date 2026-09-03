# Book Collection REST API

A small REST service for managing a book collection, built with **Python** and
**Flask**, backed by **SQLite**.

## Features

| Method | Endpoint          | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/health`         | Health check                             |
| POST   | `/books`          | Create a new book                        |
| GET    | `/books`          | List all books (supports `?author=`)     |
| GET    | `/books/{id}`     | Get a single book by ID                  |
| PUT    | `/books/{id}`     | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`     | Delete a book                            |

A **book** has the following fields:

- `title` *(string, required, non-empty)*
- `author` *(string, required, non-empty)*
- `year` *(integer, optional, 0–9999)*
- `isbn` *(string, optional, non-empty)*

## Setup

### Prerequisites

- Python 3.10+

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the server

```bash
python app.py
```

The API will be available at `http://localhost:8000`.

By default the SQLite database is created as `books.db` in the working
directory. You can override the location with the `BOOKS_DB_PATH` environment
variable:

```bash
BOOKS_DB_PATH=/tmp/books.db python app.py
```

## Usage examples

Create a book:

```bash
curl -X POST http://localhost:8000/books   -H "Content-Type: application/json"   -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'
```

List all books:

```bash
curl http://localhost:8000/books
```

Filter by author:

```bash
curl "http://localhost:8000/books?author=Andrew%20Hunt"
```

Get, update, or delete a book:

```bash
curl http://localhost:8000/books/1
curl -X PUT http://localhost:8000/books/1 -H "Content-Type: application/json" -d '{"year":2024}'
curl -X DELETE http://localhost:8000/books/1
```

## Running the tests

```bash
pytest -v
```

The test suite uses a temporary SQLite database for isolation and does **not**
touch `books.db`.

## Project layout

```
app.py            # Flask application with all routes and validation
db.py             # SQLite connection/schema helpers
test_app.py       # Unit & integration tests
requirements.txt  # Python dependencies
README.md         # This file
```
