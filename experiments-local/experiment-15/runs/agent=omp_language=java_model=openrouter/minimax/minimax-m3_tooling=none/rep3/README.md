# books-api

A small REST service for managing a personal book collection. Books are
persisted to an embedded SQLite file and exposed as JSON.

## Tech stack

- Java 21
- [Javalin 6](https://javalin.io/) on Jetty 11
- [Xerial SQLite JDBC](https://github.com/xerial/sqlite-jdbc)
- Jackson for JSON
- JUnit 5 for tests

## Project layout

```
src/main/java/com/example/books/
  Application.java             # main, wires everything together
  BookController.java          # /books + /health HTTP routes
  BookRepository.java          # SQLite CRUD
  BookInputValidator.java      # field rules
  Database.java                # connection factory + schema bootstrap
  GlobalExceptionHandler.java  # maps exceptions to HTTP status + JSON envelope
  Book.java, NotFoundException.java, ValidationException.java
src/main/resources/schema.sql  # CREATE TABLE books
src/test/java/com/example/books/
  BookApiTest.java             # end-to-end HTTP tests
  BookRepositoryTest.java      # repository tests against SQLite
  BookInputValidatorTest.java  # validator unit tests
```

## Prerequisites

- JDK 21 or newer (`java -version`)
- Maven 3.9+ (`mvn -version`)

The build downloads Javalin, SQLite JDBC, Jackson, and JUnit automatically.

## Build

```sh
mvn package
```

This compiles main and test sources, runs the test suite, and produces an
executable shaded JAR at `target/books-api.jar`.

## Run

```sh
java -jar target/books-api.jar
```

By default the server listens on port `7000` and stores its data in
`./books.db` next to the working directory. Override either with
environment variables:

| Variable   | Default      | Meaning                                                     |
|------------|--------------|-------------------------------------------------------------|
| `PORT`     | `7000`       | TCP port to bind.                                           |
| `BOOKS_DB` | `./books.db` | Path to a SQLite file. A relative path resolves from CWD.   |

Examples:

```sh
PORT=8080 BOOKS_DB=/var/data/books.db java -jar target/books-api.jar
BOOKS_DB=:memory: java -jar target/books-api.jar    # ephemeral, in-process
```

The schema is created on first start (the script in
`src/main/resources/schema.sql` is idempotent — safe to re-run).

## API

All request and response bodies are JSON. Books have the shape:

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "Tolkien",
  "year": 1937,
  "isbn": "978-0547928227"
}
```

`year` and `isbn` are optional on input and omitted from responses when
absent. `id` is server-assigned and returned by `POST` and `PUT`.

### `GET /health`

Liveness probe. Always returns `200 OK` with `{"status":"ok"}`.

```sh
curl -s http://localhost:7000/health
```

### `POST /books`

Create a book. `title` and `author` are required; `year` must be in
`[0, 9999]` if provided.

- `201 Created` — body is the new book with its assigned `id`.
- `400 Bad Request` — validation failed; body is `{"error":"validation_failed","message":"..."}`.

```sh
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}' \
  http://localhost:7000/books
```

### `GET /books`

List all books. Optional `?author=<name>` filter is case-insensitive and
matches the author field exactly (after lower-casing).

- `200 OK` — body is a JSON array (possibly empty).

```sh
curl -s http://localhost:7000/books
curl -s 'http://localhost:7000/books?author=Tolkien'
```

### `GET /books/{id}`

Fetch one book.

- `200 OK` — body is the book.
- `400 Bad Request` — `id` is not a positive integer.
- `404 Not Found` — no book with that id.

### `PUT /books/{id}`

Replace the book at `{id}`. The same validation rules as `POST` apply.
Returns the updated book on success.

- `200 OK` — body is the updated book.
- `400 Bad Request` — invalid id or invalid body.
- `404 Not Found` — no book with that id.

```sh
curl -s -X PUT -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1990,"isbn":"978-0441172719"}' \
  http://localhost:7000/books/1
```

### `DELETE /books/{id}`

Remove a book.

- `204 No Content` — deleted (no body).
- `404 Not Found` — no book with that id.

```sh
curl -s -X DELETE http://localhost:7000/books/1
```

## Error envelope

All error responses share the same JSON shape:

```json
{ "error": "<machine-readable-code>", "message": "<human-readable text>" }
```

| HTTP | `error`                | When                                       |
|------|------------------------|--------------------------------------------|
| 400  | `validation_failed`    | Missing or invalid field, or bad path id.  |
| 404  | `not_found`            | Unknown book id.                           |
| 500  | `server_error`         | Unhandled exception (logged with stack).   |

## Tests

```sh
mvn test
```

The suite runs 19 tests across three files:

- `BookInputValidatorTest` — pure unit tests for the validation rules.
- `BookRepositoryTest` — repository CRUD against a per-test SQLite file.
- `BookApiTest` — end-to-end HTTP tests driven through Javalin's
  `testtools` client, including the full create-read-update-delete
  lifecycle, the `?author=` filter, validation rejection, and 404 paths.

## Development

- Hot-reload is not configured. Run `mvn package` after edits and
  restart the JAR.
- The shaded JAR is self-contained: no classpath, no native sqlite
  install needed. The SQLite native library is loaded from inside the
  jar at startup.
- Logs are written to stdout at `INFO` level by default (SLF4J Simple).
