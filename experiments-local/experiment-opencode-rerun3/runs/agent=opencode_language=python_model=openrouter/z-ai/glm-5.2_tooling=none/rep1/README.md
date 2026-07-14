# Book Collection REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.8+
- Flask

Install dependencies:

```bash
pip install flask
```

## Running

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000`. The SQLite database file `books.db`
is created automatically on first run.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book (title, author, year, isbn) |
| GET    | `/books`        | List all books; supports `?author=` filter |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

`title` and `author` are required on create and update. Invalid input returns
`400` with an `errors` object. Missing books return `404`.

## Examples

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"1234567890"}'

curl http://127.0.0.1:5000/books
curl 'http://127.0.0.1:5000/books?author=George%20Orwell'
curl http://127.0.0.1:5000/books/1
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1950}'
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Tests

```bash
pip install pytest
pytest -v
```
