# Book Collection REST API

A REST API service for managing a book collection, written in Java using only the
JDK's built-in HTTP server — no web framework required. Data is persisted in SQLite
(via the Xerial JDBC driver) and all responses are JSON.

## Tech stack

- Java 17+ (built with `--release 17`)
- Maven 3.6+
- SQLite via `org.xerial:sqlite-jdbc`
- Gson for JSON
- JUnit 5 for integration tests

## Build

```sh
mvn clean package
```

This produces a self-contained (shaded) jar at `target/book-api.jar`.

## Run

```sh
java -jar target/book-api.jar
```

Configuration via environment variables:

| Variable   | Default    | Description          |
|------------|------------|----------------------|
| `PORT`     | `8080`     | HTTP listen port     |
| `BOOKS_DB` | `books.db` | SQLite database file |

Example:

```sh
PORT=9000 BOOKS_DB=/tmp/mybooks.db java -jar target/book-api.jar
```

## Test

```sh
mvn test
```

The test suite (`src/test/java/com/example/books/BookApiTest.java`) starts the
server on an ephemeral port with a temporary SQLite database and exercises the
full HTTP API: health check, create, validation errors, list + author filter,
get by id, update, and delete.

## API

| Method   | Path          | Description                        | Success | Errors        |
|----------|---------------|------------------------------------|---------|---------------|
| `GET`    | `/health`     | Health check                       | `200`   | —             |
| `POST`   | `/books`      | Create a book                      | `201`   | `400`         |
| `GET`    | `/books`      | List all books (`?author=` filter) | `200`   | —             |
| `GET`    | `/books/{id}` | Get a book by id                   | `200`   | `404`         |
| `PUT`    | `/books/{id}` | Update a book                      | `200`   | `400`, `404`  |
| `DELETE` | `/books/{id}` | Delete a book                      | `204`   | `404`         |

### Book JSON

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780547928227"
}
```

- `title` and `author` are **required** (missing/blank → `400 {"error": "..."}`).
- `year` (integer) and `isbn` (string) are optional.
- `id` is assigned by the server on create.

### Examples

```sh
# Health check
curl http://localhost:8080/health

# Create
curl -X POST -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}' \
  http://localhost:8080/books

# List all / filter by author
curl http://localhost:8080/books
curl "http://localhost:8080/books?author=Frank%20Herbert"

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}' \
  http://localhost:8080/books/1

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Project layout

```
pom.xml
src/main/java/com/example/books/
  BookApiServer.java    — entry point, HTTP server wiring
  BookHandler.java      — /books routing, validation, JSON responses
  HealthHandler.java    — GET /health
  BookRepository.java   — SQLite persistence (JDBC)
  Book.java             — book model
src/test/java/com/example/books/
  BookApiTest.java      — end-to-end HTTP integration tests
```
