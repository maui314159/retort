# Book Collection API

A small REST API service for managing a book collection, written in Go. Books are stored in a local SQLite database.

## Features

- `POST /books` — create a new book
- `GET /books` — list all books, optionally filtered by `?author=`
- `GET /books/{id}` — get a single book
- `PUT /books/{id}` — update a book
- `DELETE /books/{id}` — delete a book
- `GET /health` — health check

Input validation ensures `title` and `author` are non-empty.

## Requirements

- [Go](https://go.dev/) 1.22 or later

## Run

```bash
go run .
```

The server starts on `http://localhost:8080` and creates `books.db` in the working directory.

## Test

```bash
go test ./...
```

## Example usage

Create a book:

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'
```

List books:

```bash
curl http://localhost:8080/books
```

Filter by author:

```bash
curl "http://localhost:8080/books?author=Orwell"
```

Get a book:

```bash
curl http://localhost:8080/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:8080/books/1
```

Health check:

```bash
curl http://localhost:8080/health
```
