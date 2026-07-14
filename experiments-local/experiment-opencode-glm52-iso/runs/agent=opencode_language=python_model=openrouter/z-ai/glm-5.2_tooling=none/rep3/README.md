# Book Collection REST API

A small REST service for managing a book collection, built with Flask and SQLite.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | /health         | Health check                         |
| POST   | /books          | Create a book (title, author, year, isbn) |
| GET    | /books          | List all books; supports `?author=` filter |
| GET    | /books/{id}     | Get a single book                    |
| PUT    | /books/{id}     | Update a book                        |
| DELETE | /books/{id}     | Delete a book                        |

`title` and `author` are required on POST and PUT.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask pytest
```

## Run

```bash
python app.py
# serves on http://0.0.0.0:5000
```

The SQLite database file defaults to `books.db` in the working directory;
override with the `BOOKS_DB_PATH` environment variable.

## Tests

```bash
pytest -v
```
