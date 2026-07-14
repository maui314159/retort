# Book Collection REST API

A small REST service for managing a book collection, built with **Spring Boot 3.4**
and **SQLite** (via the `sqlite-jdbc` driver and Spring's `JdbcTemplate`).

## Endpoints

| Method | Path             | Description                                  | Status codes        |
|--------|------------------|----------------------------------------------|---------------------|
| POST   | `/books`         | Create a new book                            | `201`, `400`        |
| GET    | `/books`         | List all books; supports `?author=` filter    | `200`               |
| GET    | `/books/{id}`    | Get a single book by id                      | `200`, `404`        |
| PUT    | `/books/{id}`    | Update a book                                | `200`, `400`, `404` |
| DELETE | `/books/{id}`    | Delete a book                                | `204`, `404`        |
| GET    | `/books/health`  | Health check                                 | `200`               |

### Book model

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

### Validation

- `title` — required, non-blank
- `author` — required, non-blank
- `year` — optional, must be a positive number when present
- `isbn` — optional

Invalid input returns `400` with a JSON body describing the field errors, e.g.:

```json
{
  "status": 400,
  "error": "Bad Request",
  "errors": { "title": "title is required" }
}
```

## Prerequisites

- **JDK 17+** (tested with JDK 26)
- **Maven 3.9+**
- `sqlite3` CLI (optional, only for inspecting the database file)

## Setup & run

```bash
# from the project directory
./mvnw spring-boot:run        # if using the wrapper, or:
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A `books.db` SQLite file is
created next to the application on first run; the `books` table is created
automatically on startup.

### Configuration (optional)

| Property            | Env var       | Default                      |
|---------------------|---------------|------------------------------|
| `spring.datasource.url` | `BOOK_DB_URL` | `jdbc:sqlite:books.db`       |
| `server.port`       | `PORT`        | `8080`                       |

Example: run against an in-memory database on port 9090.

```bash
BOOK_DB_URL="jdbc:sqlite::memory:" PORT=9090 mvn spring-boot:run
```

## Build & test

```bash
mvn clean verify
```

This compiles the code and runs the test suite (integration, validation, and
repository tests). The tests spin up isolated on-disk SQLite databases so they
do not touch the application's `books.db`.

## Example usage

```bash
# Create a book
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}'

# List all books
curl -s http://localhost:8080/books

# Filter by author
curl -s 'http://localhost:8080/books?author=Herbert'

# Get / update / delete by id
curl -s http://localhost:8080/books/1
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (rev)","author":"Herbert","year":1965,"isbn":"9780441172719"}'
curl -s -X DELETE http://localhost:8080/books/1

# Health check
curl -s http://localhost:8080/books/health
```

## Project layout

```
src/main/java/com/example/bookapi/
├── BookApiApplication.java          # Spring Boot entry point
├── controller/BookController.java   # REST endpoints
├── dto/BookRequest.java             # validated request body
├── exception/                        # BookNotFoundException + global advice
├── model/Book.java                  # immutable book record
└── repository/BookRepository.java   # JDBC persistence
src/main/resources/
├── application.properties
└── schema.sql
src/test/java/com/example/bookapi/   # integration, validation, repository tests
```
