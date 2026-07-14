# books-api

A small REST API for managing a book collection, built with **Spring Boot 3** and
backed by an embedded **SQLite** database. No external services required.

## Tech stack

- Java 17+ (tested on OpenJDK 25)
- Spring Boot 3.3.5 (Web, JDBC, Validation)
- SQLite via [xerial/sqlite-jdbc](https://github.com/xerial/sqlite-jdbc)
- JUnit 5 (Spring Boot Test, MockMvc)

## Requirements

- JDK 17 or newer
- Maven 3.8+

## Build

```bash
mvn -B package
```

The runnable fat jar lands at `target/books-api-0.0.1-SNAPSHOT.jar`.

## Run

```bash
java -jar target/books-api-0.0.1-SNAPSHOT.jar
# or
mvn -B spring-boot:run
```

The service listens on `http://localhost:8080`.

The SQLite file defaults to `./data/books.db`. The parent directory is created
automatically on startup. Override the path with the `BOOKS_DB` environment
variable (full JDBC URL):

```bash
BOOKS_DB=jdbc:sqlite:/var/tmp/books.db java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

To use a fully in-memory database, pass a JDBC URL directly:

```bash
SPRING_DATASOURCE_URL=jdbc:sqlite::memory: java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

## API

| Method | Path              | Description                                | Success | Errors       |
| ------ | ----------------- | ------------------------------------------ | ------- | ------------ |
| GET    | `/health`         | Liveness probe                             | 200     | —            |
| POST   | `/books`          | Create a book                              | 201     | 400          |
| GET    | `/books`          | List books; `?author=<name>` filters       | 200     | —            |
| GET    | `/books/{id}`     | Fetch one book                             | 200     | 404          |
| PUT    | `/books/{id}`     | Replace a book                             | 200     | 400, 404     |
| DELETE | `/books/{id}`     | Remove a book                              | 204     | 404          |

### Book payload

```json
{
  "title":  "Dune",
  "author": "Frank Herbert",
  "year":   1965,
  "isbn":   "0441172717"
}
```

- `title` (string, **required**, non-blank)
- `author` (string, **required**, non-blank)
- `year` (int, optional, must be ≥ 1 if present)
- `isbn` (string, optional)

The `id` is assigned by the server on create and echoed on every read/update.

### Error body

Validation, malformed JSON, and not-found errors all share this shape:

```json
{
  "timestamp": "2026-06-13T16:55:32.047280Z",
  "status":    400,
  "error":     "Bad Request",
  "message":   "author: author is required"
}
```

### Examples

```bash
# Create
curl -i -X POST http://localhost:8080/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0441172717"}'

# List (all)
curl http://localhost:8080/books

# List (filtered)
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Fetch one
curl http://localhost:8080/books/1

# Update
curl -i -X PUT http://localhost:8080/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune (2nd ed.)","author":"Frank Herbert","year":1969,"isbn":"0441172717"}'

# Delete
curl -i -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn -B test
```

The suite contains 18 tests across three classes:

- `BookApiIntegrationTest` — boots a real Spring context and exercises the full
  HTTP surface (CRUD lifecycle, `?author=` filter, validation, 404s, malformed
  JSON) using `MockMvc`.
- `BookRepositoryTest` — direct JDBC-level tests of the repository.
- `BookValidationTest` — pure unit tests of the bean validation constraints
  declared on `Book` (no Spring context).

Tests run against an in-memory SQLite database (`jdbc:sqlite::memory:`).

## Project layout

```
src/main/java/com/example/books/
  BooksApplication.java       # Spring Boot entry point
  Book.java                   # @NotBlank-validated entity / DTO
  BookRepository.java         # JdbcTemplate-backed persistence
  BookController.java         # /books endpoints
  HealthController.java       # /health endpoint
  BookNotFoundException.java  # 404 mapping
  GlobalExceptionHandler.java # @RestControllerAdvice for 400/404
  SqliteDirEnsurer.java       # BeanFactoryPostProcessor — creates ./data
src/main/resources/
  application.yml             # Spring config (port, datasource)
  schema.sql                  # CREATE TABLE book
src/test/java/com/example/books/
  BookApiIntegrationTest.java
  BookRepositoryTest.java
  BookValidationTest.java
```

## Configuration knobs

| Property                  | Default                  | Notes                                 |
| ------------------------- | ------------------------ | ------------------------------------- |
| `server.port`             | `8080`                   |                                       |
| `spring.datasource.url`   | `jdbc:sqlite:${BOOKS_DB:./data/books.db}` | SQLite JDBC URL        |
| `BOOKS_DB`                | `./data/books.db`        | Used by the default URL only          |
