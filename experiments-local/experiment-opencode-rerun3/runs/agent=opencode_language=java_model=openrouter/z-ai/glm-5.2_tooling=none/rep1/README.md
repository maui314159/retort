# Books Service

A small REST API for managing a book collection, built with **Spring Boot 3** and **SQLite** (via `sqlite-jdbc` + Spring `JdbcTemplate`).

## Requirements

- Java 17+ (tested on Java 17 and 26)
- Maven 3.8+ (the project bundles the Spring Boot Maven plugin)

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db` is created automatically in the working directory on first run (the `books` table is created on startup if it does not exist).

## API

| Method | Path              | Description                       |
|--------|-------------------|-----------------------------------|
| GET    | `/health`         | Health check (`{"status":"UP"}`) |
| POST   | `/books`          | Create a book (201)              |
| GET    | `/books`          | List all books; supports `?author=` filter (200) |
| GET    | `/books/{id}`     | Get a single book (200 / 404)    |
| PUT    | `/books/{id}`     | Update a book (200 / 404)        |
| DELETE | `/books/{id}`     | Delete a book (204 / 404)        |

### Book JSON

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required and validated. `year` must be a non-negative integer if present. `isbn` is optional.

### Example

```bash
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}'

curl -s 'http://localhost:8080/books?author=J.R.R.%20Tolkien'
```

## Tests

```bash
mvn test
```

Integration tests (`BookControllerTest`) use a separate SQLite file at `target/test-books.db` (via the `test` Spring profile) and cover:

1. Health endpoint.
2. Create + fetch a book by id.
3. Listing with `?author=` filter.
4. Update.
5. Delete (and subsequent 404).
6. Input validation (missing `title`/`author` -> 400).
7. Not-found handling (404).

## Project layout

```
src/main/java/com/example/books
  BooksApplication.java          # entry point
  config/SchemaConfig.java       # creates the books table on startup
  controller/BookController.java # /books endpoints
  controller/HealthController.java # /health
  dto/BookRequest.java           # validated request body
  model/Book.java                # domain object
  repository/BookRepository.java # JdbcTemplate access
  service/BookService.java       # business logic
  exception/                     # not-found + global exception handling
src/main/resources/application.properties
src/test/...                     # integration tests
```
