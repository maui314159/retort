# Book Collection REST API

A small REST API for managing a book collection, built with Python and Flask,
backed by an embedded SQLite database.

## Requirements

- Python 3.8+
- Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

## Running the service

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000`. A SQLite file `books.db` is
created automatically in the working directory on first run.

## Endpoints

| Method   | Path             | Description                          |
|----------|------------------|--------------------------------------|
| `GET`    | `/health`        | Health check                         |
| `POST`   | `/books`         | Create a book                        |
| `GET`    | `/books`         | List books (supports `?author=`)     |
| `GET`    | `/books/{id}`    | Get a single book                    |
| `PUT`    | `/books/{id}`    | Update a book (partial updates OK)   |
| `DELETE` | `/books/{id}`    | Delete a book                        |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required on create; all other fields are optional.
`year` must be an integer when provided.

### Example

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
```

## Status codes

- `200` — successful read/update
- `201` — created
- `204` — deleted
- `400` — validation error (JSON body with `errors`)
- `404` — book not found

## Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Each test runs against an isolated temporary SQLite database so the suite is
idempotent and safe to re-run.
