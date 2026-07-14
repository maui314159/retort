# Book API

A small REST API service for managing a book collection, written in Java using only the JDK's built-in `com.sun.net.httpserver.HttpServer`, SQLite (via `sqlite-jdbc`) for storage, and Jackson for JSON.

## Requirements

- Java 17+ (built and tested on JDK 17 release target)
- Maven 3.6+

## Endpoints

| Method   | Path           | Description                              |
|----------|----------------|------------------------------------------|
| `GET`    | `/health`      | Health check                             |
| `POST`   | `/books`       | Create a book (`title`, `author`, `year`, `isbn`) |
| `GET`    | `/books`       | List all books (supports `?author=` filter) |
| `GET`    | `/books/{id}`  | Get a single book by ID                  |
| `PUT`    | `/books/{id}`  | Update a book                            |
| `DELETE` | `/books/{id}`  | Delete a book                            |

### Validation

`title` and `author` are required on `POST` and `PUT` (blank/missing values return `400 Bad Request`). `year` (integer) and `isbn` (string) are optional.

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error
- `404 Not Found` — book not found
- `405 Method Not Allowed` — unsupported method
- `500 Internal Server Error` — unexpected error

## Build

```bash
mvn clean package
```

## Run

```bash
mvn exec:java -Dexec.mainClass=com.example.books.Main
# or
java -jar target/book-api-1.0.0.jar
```

### Options

| Flag / Env Var         | Default     | Description                  |
|------------------------|-------------|------------------------------|
| `--port <n>` / `BOOKAPI_PORT` | `8080` | Port to listen on            |
| `--db <path>` / `BOOKAPI_DB`  | `books.db` | Path to the SQLite database file |

The SQLite database file is created automatically on first run.

## Test

```bash
mvn test
```

Tests include unit tests for the repository layer and integration tests that boot the HTTP server on an ephemeral port against a temporary SQLite file.

## Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl http://localhost:8080/books?author=Frank%20Herbert
```
