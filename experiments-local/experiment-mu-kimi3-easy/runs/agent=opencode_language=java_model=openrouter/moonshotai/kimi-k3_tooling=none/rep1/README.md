# Book Service

A small REST API for managing a book collection, written in Java. It uses the
JDK's embedded HTTP server (`com.sun.net.httpserver`) — no web framework — and
stores data in SQLite via JDBC.

## Requirements

- JDK 21 or newer
- Maven 3.8+

## Run

```sh
mvn compile exec:java
```

The service listens on `http://localhost:8080` and creates `books.db` in the
working directory on first start.

Configuration via environment variables:

| Variable   | Default    | Description          |
|------------|------------|----------------------|
| `PORT`     | `8080`     | HTTP port            |
| `BOOKS_DB` | `books.db` | SQLite database file |

Example: `PORT=9000 BOOKS_DB=/tmp/my.db mvn compile exec:java`

## Test

```sh
mvn test
```

Integration tests boot the real server on an ephemeral port with a temporary
SQLite file and exercise the API over HTTP (health check, CRUD, validation,
author filtering, 404 handling).

## API

All request and response bodies are JSON. Errors are returned as
`{"error": "<message>"}`.

| Method   | Path             | Description                    | Success status |
|----------|------------------|--------------------------------|----------------|
| `GET`    | `/health`        | Health check                   | `200`          |
| `POST`   | `/books`         | Create a book                  | `201`          |
| `GET`    | `/books`         | List books (`?author=` filter) | `200`          |
| `GET`    | `/books/{id}`    | Get one book                   | `200`          |
| `PUT`    | `/books/{id}`    | Update a book (full replace)   | `200`          |
| `DELETE` | `/books/{id}`    | Delete a book                  | `204`          |

### Book fields

| Field    | Type    | Required | Notes                        |
|----------|---------|----------|------------------------------|
| `id`     | integer | —        | Assigned by the server       |
| `title`  | string  | yes      | Non-blank                    |
| `author` | string  | yes      | Non-blank                    |
| `year`   | integer | no       | May be `null`                |
| `isbn`   | string  | no       | May be `null`                |

Missing/blank `title` or `author`, and malformed JSON, return `400`.
Unknown ids return `404`. Unsupported methods return `405`.

### Examples

```sh
# Health
curl http://localhost:8080/health

# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List (all / filtered by author)
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Project layout

```
src/main/java/com/books/
├── App.java              # entry point (env config, lifecycle)
├── BookServer.java       # HTTP server, routing, JSON (de)serialization
├── Book.java             # book model
└── BookRepository.java   # SQLite persistence (JDBC)
src/test/java/com/books/
└── BookApiTest.java      # HTTP integration tests (JUnit 5)
```
