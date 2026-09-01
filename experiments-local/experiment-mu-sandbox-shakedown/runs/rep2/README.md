# Books REST API

A REST API service for managing a book collection, built with Python and
Flask, backed by an embedded SQLite database.

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000`. Set the `PORT` environment
variable to use a different port:

```bash
PORT=8080 python app.py
```

Alternatively, run with Flask's CLI:

```bash
flask --app app run
```

Data is stored in `books.db` in the working directory. Set `BOOKS_DB` to
change the database location:

```bash
BOOKS_DB=/tmp/books.db python app.py
```

## API

| Method | Endpoint       | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Health check                                  |
| POST   | `/books`       | Create a book (`title`, `author` required)    |
| GET    | `/books`       | List all books, optional `?author=` filter    |
| GET    | `/books/{id}`  | Get a single book                             |
| PUT    | `/books/{id}`  | Update a book (`title`, `author` required)    |
| DELETE | `/books/{id}`  | Delete a book                                 |

A book has the fields `title` (string, required), `author` (string,
required), `year` (integer, optional) and `isbn` (string, optional).
The `?author=` filter performs a case-insensitive substring match.

Status codes: `200` OK, `201` Created, `204` No Content (delete), `400`
validation error, `404` not found.

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
```

List books, filtered by author:

```bash
curl "http://localhost:5000/books?author=herbert"
```

Get, update and delete a book:

```bash
curl http://localhost:5000/books/1

curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -X DELETE http://localhost:5000/books/1
```

## Tests

```bash
pytest -v
```

The tests use a temporary SQLite database via the application factory, so
they do not touch `books.db`.
