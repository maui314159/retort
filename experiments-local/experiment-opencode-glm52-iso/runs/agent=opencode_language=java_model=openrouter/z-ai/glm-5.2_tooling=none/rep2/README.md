# Books API

A REST API service for managing a book collection, written in Java using the JDK
built-in HTTP server, SQLite (via JDBC) for storage, and Jackson for JSON.

## Requirements

- JDK 17+ (built and tested on OpenJDK 26)
- Maven 3.6+

## Setup & Run

Build the project and run the tests:

```bash
mvn clean package
```

Run the server (defaults to port 8080, SQLite file `books.db` in the working dir):

```bash
mvn exec:java
```

Override configuration via environment variables:

```bash
PORT=9090 DB_URL=jdbc:sqlite:/tmp/books.db mvn exec:java
```

To use an in-memory database (data is lost on restart):

```bash
DB_URL=jdbc:sqlite::memory: mvn exec:java
```

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book (title, author, year, isbn) |
| GET    | `/books`        | List books (supports `?author=` filter) |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}'

curl 'http://localhost:8080/books?author=J.R.R.%20Tolkien'
```

## Validation

- `title` and `author` are required (non-blank). Returns `400` with a JSON error
  body describing the offending field.
- `year`, if provided, must be between 0 and 9999.
- Operating on a non-existent book id returns `404`.

## Status codes

- `200` — successful GET/PUT
- `201` — book created
- `204` — book deleted (empty body)
- `400` — validation error
- `404` — resource not found
- `405` — method not allowed
- `500` — server/database error

## Tests

The project ships three test classes (run with `mvn test`):

- `DatabaseTest` — SQLite CRUD operations.
- `BookServiceTest` — service-level validation and not-found handling.
- `BookApiIT` — end-to-end HTTP tests covering the full lifecycle, author
  filtering, input validation, and 404 behavior.

## Project layout

```
src/main/java/com/example/
  Main.java            - entrypoint, starts the server
  Router.java          - HTTP routing + JSON serialization
  BookService.java     - validation + business logic
  Database.java        - SQLite access layer
  Book.java            - model
  ValidationException.java
  NotFoundException.java
src/test/java/com/example/
  DatabaseTest.java
  BookServiceTest.java
  BookApiIT.java
```
