# Book Collection Service

A REST API for managing a book collection, written in Java. Books are stored in an
embedded SQLite database via JDBC; the HTTP layer uses the JDK's built-in
`com.sun.net.httpserver` (no web framework required), and Jackson handles JSON.

## Requirements

- JDK 17 or newer
- Maven 3.6 or newer

## Build

```sh
mvn package
```

This compiles the code, runs the tests, and produces a self-contained executable jar
at `target/book-service.jar`.

## Run

```sh
java -jar target/book-service.jar
```

Configuration (environment variables):

| Variable | Default               | Description          |
|----------|-----------------------|----------------------|
| `PORT`   | `8080`                | HTTP listen port     |
| `DB_URL` | `jdbc:sqlite:books.db` | JDBC connection URL |

Example: `PORT=9000 DB_URL="jdbc:sqlite:/tmp/my.db" java -jar target/book-service.jar`

## Test

```sh
mvn test
```

Runs 7 integration tests that start the real server on an ephemeral port backed by an
in-memory SQLite database and exercise every endpoint over HTTP.

## API

All request and response bodies are JSON. Errors are returned as `{"error": "..."}`.

| Method | Path             | Description                              | Success | Error codes        |
|--------|------------------|------------------------------------------|---------|--------------------|
| GET    | `/health`        | Health check                             | 200     | 405                |
| POST   | `/books`         | Create a book                            | 201     | 400                |
| GET    | `/books`         | List books; `?author=` filters by author | 200     | —                  |
| GET    | `/books/{id}`    | Get one book                             | 200     | 400, 404           |
| PUT    | `/books/{id}`    | Replace a book                           | 200     | 400, 404           |
| DELETE | `/books/{id}`    | Delete a book                            | 204     | 400, 404           |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional). `id` is assigned by the server.

### Examples

```sh
# Health check
curl http://localhost:8080/health
# => {"status":"ok"}

# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}'
# => 201 {"id":1,"title":"Clean Code",...}

# List all / filter by author
curl http://localhost:8080/books
curl "http://localhost:8080/books?author=Robert%20C.%20Martin"

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Clean Code (2nd)","author":"Robert C. Martin","year":2009}'

# Delete
curl -X DELETE http://localhost:8080/books/1   # => 204
```

## Project layout

```
pom.xml                                     Maven build (deps: sqlite-jdbc, jackson, junit)
src/main/java/com/example/books/
  Main.java                                 Entry point: wires repository + server
  BookApiServer.java                        HTTP routing, validation, JSON, status codes
  BookRepository.java                       SQLite CRUD via JDBC
  Book.java                                 Book model
src/test/java/com/example/books/
  BookApiServerTest.java                    End-to-end HTTP tests
```
