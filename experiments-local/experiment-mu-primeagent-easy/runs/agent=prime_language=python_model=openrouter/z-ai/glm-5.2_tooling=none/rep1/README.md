# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Endpoints

| Method   | Path           | Description                          |
|----------|----------------|--------------------------------------|
| `GET`    | `/health`      | Health check                         |
| `POST`   | `/books`       | Create a new book                    |
| `GET`    | `/books`       | List all books (supports `?author=`) |
| `GET`    | `/books/{id}`  | Get a single book by ID              |
| `PUT`    | `/books/{id}`  | Update a book                        |
| `DELETE` | `/books/{id}`  | Delete a book                        |

### Book fields

| Field  | Type    | Required | Notes                         |
|--------|---------|----------|-------------------------------|
| title  | string  | yes      | Must not be empty             |
| author | string  | yes      | Must not be empty             |
| year   | integer | no       | Non-negative integer          |
| isbn   | string  | no       | Free-form ISBN string         |

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service starts on `http://0.0.0.0:5000`. The SQLite database file
`books.db` is created in the working directory on first run. Override the
database path with the `BOOKS_DB_PATH` environment variable if needed:

```bash
BOOKS_DB_PATH=/tmp/my_books.db python app.py
```

## Example

```bash
curl -X POST http://localhost:5000/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0-13-235088-4"}'

curl http://localhost:5000/books
curl 'http://localhost:5000/books?author=Robert%20C.%20Martin'
curl http://localhost:5000/books/1
```

## Tests

```bash
python -m pytest -v
```
