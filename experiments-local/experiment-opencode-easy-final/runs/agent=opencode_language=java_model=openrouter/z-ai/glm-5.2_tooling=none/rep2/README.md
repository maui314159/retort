# Books REST API

A small REST API service for managing a book collection, implemented in Java
using the JDK's built-in `com.sun.net.httpserver` HTTP server, SQLite (via the
`sqlite-jdbc` driver) for storage, and Jackson for JSON serialization.

## Endpoints

| Method | Path             | Description                              |
|--------|------------------|------------------------------------------|
| GET    | `/health`        | Health check (`{"status":"ok"}`)        |
| POST   | `/books`         | Create a new book (title, author, year, isbn) |
| GET    | `/books`         | List all books; supports `?author=` filter |
| GET    | `/books/{id}`    | Get a single book by ID (404 if missing) |
| PUT    | `/books/{id}`    | Update a book (404 if id unknown)       |
| DELETE | `/books/{id}`    | Delete a book (204 on success, 404 otherwise) |

### Validation
`title` and `author` are required. Missing or blank values return HTTP `400`
with a JSON body such as `{"error":"title is required","status":400}`.

### Status codes
- `200` OK (successful GET/PUT)
- `201` Created (POST)
- `204` No Content (DELETE)
- `400` Bad Request (validation error)
- `404` Not Found (unknown id)
- `405` Method Not Allowed
- `500` Internal Server Error

## Requirements
- Java 21 or later (built and tested on OpenJDK 26)
- Apache Maven 3.6+
- Internet access on first build (Maven downloads dependencies from Maven Central)

## Build

```sh
mvn clean package
```

This compiles the sources, runs the tests, and produces:
- `target/books-api-1.0.0.jar` — self-contained executable (shaded) jar with all dependencies
- `target/original-books-api-1.0.0.jar` — plain unshaded jar (for reference only)

## Run

```sh
# Using the shaded executable jar (recommended):
java -jar target/books-api-1.0.0.jar
```

The server listens on `http://localhost:8080` by default.

### Configuration (environment variables)
| Variable         | Default     | Description                       |
|------------------|-------------|-----------------------------------|
| `PORT`           | `8080`      | HTTP listen port                  |
| `BOOKS_DB_PATH`  | `books.db`  | SQLite database file path         |

Use `:memory:` for an in-memory database that is wiped on restart.

## Tests

```sh
mvn test
```

Five tests are included, covering the repository, the HTTP lifecycle
(create/list/get/update/delete), the author filter, validation errors, and the
health endpoint.

## Example usage

```sh
# Health
curl http://localhost:8080/health

# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one (replace 1 with the id returned by POST)
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"X"}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```
