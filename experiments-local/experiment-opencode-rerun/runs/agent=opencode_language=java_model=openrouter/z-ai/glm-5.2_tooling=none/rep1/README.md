# Bookstore REST API

A small REST API service for managing a book collection, written in Java with the
built-in JDK HTTP server and SQLite for storage. No servlet container or Spring
runtime is required — just run the jar.

## Endpoints

| Method   | Route         | Description                              |
|---------|---------------|------------------------------------------|
| GET     | `/health`     | Health check (returns `{"status":"up"}`) |
| POST    | `/books`      | Create a new book                        |
| GET     | `/books`      | List all books; supports `?author=` filter |
| GET     | `/books/{id}` | Get a single book by ID                  |
| PUT     | `/books/{id}` | Update a book                            |
| DELETE  | `/books/{id}` | Delete a book (returns `204 No Content`) |

### Book JSON shape

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt & Thomas",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required. `year` (0–9999) and `isbn` (≤ 32 chars) are
optional. Invalid input is rejected with `400` and a JSON `{"errors":[...]}` body.
Missing books return `404`.

## Prerequisites

- Java 17 or newer (built/tested on OpenJDK 26)
- Apache Maven 3.6+

## Build

```sh
mvn package
```

This compiles the code, runs the test suite, and produces a shaded (fat) jar at
`target/bookstore-1.0.0.jar` that contains all dependencies.

## Run

```sh
java -jar target/bookstore-1.0.0.jar
```

By default the service listens on `http://localhost:8080` and writes data to a
file `books.db` in the current working directory. You can override via env
vars:

```sh
PORT=8080 DB_URL=jdbc:sqlite:books.db java -jar target/bookstore-1.0.0.jar
```

Use `jdbc:sqlite::memory:` for an ephemeral in-memory database (great for
throwaway demos).

## Examples

```sh
# health
curl -s http://localhost:8080/health

# create
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Fowler","year":1999,"isbn":"978-0-20-148567-7"}'

# list
curl -s http://localhost:8080/books

# filter by author
curl -s 'http://localhost:8080/books?author=Fowler'

# get one
curl -s http://localhost:8080/books/1

# update
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring (2nd)","author":"Fowler","year":2018,"isbn":"978-0134757777"}'

# delete
curl -s -X DELETE http://localhost:8080/books/1 -i
```

## Tests

Three test classes under `src/test/java/com/example/bookstore/`:

- `BookDaoTest` — SQLite DAO CRUD (in-memory database), including filtering,
  updates of nonexistent ids, null year/isbn handling.
- `ValidatorTest` — required-field validation, year range, ISBN length, null body.
- `BookStoreHandlerIntegrationTest` — boots a real `HttpServer` on an ephemeral
  port and exercises the full HTTP surface (health, create/list/get/update/delete
  round-trip, 400 validation/malformed-JSON, 404 missing, routing).

Run them with:

```sh
mvn test
```

## Project layout

```
pom.xml
src/main/java/com/example/bookstore/
  Main.java                # entrypoint: boots HttpServer + initializes SQLite
  Book.java                # model
  BookDao.java             # plain-JDBC SQLite repository
  Validator.java           # input validation rules
  Json.java                # Jackson wrapper
  BookStoreHandler.java   # HttpHandler that routes + serializes JSON
src/test/java/com/example/bookstore/
  BookDaoTest.java
  ValidatorTest.java
  BookStoreHandlerIntegrationTest.java
```
