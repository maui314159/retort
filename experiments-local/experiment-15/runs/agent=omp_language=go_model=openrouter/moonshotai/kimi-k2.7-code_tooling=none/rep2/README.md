# Books API

A simple REST API service for managing a book collection, written in Go with SQLite storage.

## Features

- Create, read, update, and delete books
- List all books with optional `?author=` filter
- Input validation for required fields
- Health check endpoint
- SQLite embedded database

## Requirements

- Go 1.22 or later
- A C compiler for building the SQLite driver (usually available on macOS/Linux)

## Running the service

```bash
go run .
```

The server starts on port `8080` by default. Change the port with the `PORT` environment variable:

```bash
PORT=3000 go run .
```

The SQLite database file is created as `books.db` in the working directory. Use `DB_FILE` to customize:

```bash
DB_FILE=/tmp/books.db go run .
```

## API endpoints

| Method | Endpoint        | Description                      |
|--------|-----------------|----------------------------------|
| GET    | /health         | Health check                     |
| POST   | /books          | Create a new book                |
| GET    | /books          | List all books                   |
| GET    | /books/{id}     | Get a single book by ID          |
| PUT    | /books/{id}     | Update a book                    |
| DELETE | /books/{id}     | Delete a book                    |

### Example requests

Create a book:

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0134190440"}'
```

List books:

```bash
curl http://localhost:8080/books
```

Filter by author:

```bash
curl "http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan"
```

Get a book:

```bash
curl http://localhost:8080/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2016,"isbn":"978-0134190440"}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Running tests

```bash
go test ./...
```

Tests use an in-memory SQLite database and cover health, CRUD operations, validation, and filtering.
