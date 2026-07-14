# Books Service

A REST API service for managing a book collection, built with **Spring Boot 3.5** and **SQLite**.

## Requirements

- Java 17+ (tested with JDK 26)
- Maven 3.6+
- SQLite (provided automatically via the `sqlite-jdbc` driver — no system install required)

## Run

```bash
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db`
is created in the working directory on first run.

## Build & Test

```bash
mvn clean package   # builds the jar
mvn test            # runs unit/integration tests
```

Tests use an in-memory SQLite database (`jdbc:sqlite::memory:`) and Spring's
`MockMvc`, so they run without touching the production `books.db` file.

## API

| Method | Path                 | Description                                     |
|--------|----------------------|-------------------------------------------------|
| GET    | `/health`           | Health check — returns `{"status":"UP"}` (200)  |
| POST   | `/books`             | Create a book (201) — body: `{title, author, year, isbn}` |
| GET    | `/books`             | List all books (200); supports `?author=` filter |
| GET    | `/books/{id}`       | Get a single book (200) or 404 if not found     |
| PUT    | `/books/{id}`       | Update a book (200) or 404 if not found         |
| DELETE | `/books/{id}`        | Delete a book (204) or 404 if not found         |

### Validation

`title` and `author` are required. A missing/blank field returns `400 Bad Request`
with a JSON body listing the field errors, e.g.:

```json
{ "status": 400, "error": "Bad Request", "errors": { "title": "must not be blank" } }
```

### Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}'

curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Robert%20C.%20Martin'
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Uncle Bob","year":2008,"isbn":"978-0132350884"}'
curl -X DELETE http://localhost:8080/books/1
```

## Project Layout

```
src/main/java/com/example/books
  BooksApplication.java             -- Spring Boot entry point
  model/Book.java                   -- JPA entity with validation
  repository/BookRepository.java    -- Spring Data JPA repository
  controller/BookController.java    -- CRUD endpoints
  controller/HealthController.java  -- /health
  controller/GlobalExceptionHandler.java -- 400 validation responses
src/main/resources/application.properties
src/test/java/com/example/books    -- integration tests
```

## Tests

- `BookRepositoryIntegrationTest` — save/findById, author filter, delete (3 tests)
- `BookControllerIntegrationTest` — health, CRUD, validation 400, 404, author filter (7 tests)

Run with `mvn test`.
