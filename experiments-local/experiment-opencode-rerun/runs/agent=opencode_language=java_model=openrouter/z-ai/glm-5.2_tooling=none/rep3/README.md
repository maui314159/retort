# Books API

A Spring Boot REST service for managing a book collection, backed by SQLite.

## Requirements

- Java 17+ (tested with OpenJDK 26)
- Maven 3.6+

## Build & Run

```bash
# from the project root
mvn clean package        # builds the jar and runs tests
java -jar target/books-api-0.0.1-SNAPSHOT.jar   # starts the server on :8080
# or run directly:
mvn spring-boot:run
```

The SQLite database file `books.db` is created in the working directory on first
run. Delete it to reset the data.

## Endpoints

| Method | Path                       | Description                            | Status codes          |
|--------|----------------------------|----------------------------------------|-----------------------|
| POST   | `/books`                  | Create a book                          | 201, 400 on bad input |
| GET    | `/books`                  | List all books (supports `?author=`)  | 200                   |
| GET    | `/books/{id}`            | Get a single book                      | 200, 404 if missing  |
| PUT    | `/books/{id}`            | Update a book                          | 200, 400, 404        |
| DELETE | `/books/{id}`            | Delete a book                          | 204, 404 if missing  |
| GET    | `/health`                | Health check                           | 200                   |

### Book JSON shape

```json
{
  "title": "The Pragmatic Programmer",
  "author": "Hunt & Thomas",
  "year": 2019,
  "isbn": "978-0135957059"
}
```

`title` and `author` are required (non-blank). `year` and `isbn` are optional.
On validation failure the API returns `400` with a body of the form:

```json
{
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "details": { "title": "title is required" }
}
```

## Examples

```bash
# create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Fowler","year":1999,"isbn":"0-201-48567-2"}'

# list all
curl http://localhost:8080/books

# filter by author
curl 'http://localhost:8080/books?author=Fowler'

# get one
curl http://localhost:8080/books/1

# update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring (2nd ed.)","author":"Fowler","year":2018,"isbn":"x"}'

# delete
curl -X DELETE http://localhost:8080/books/1

# health
curl http://localhost:8080/health
```

## Tests

Integration tests use `@SpringBootTest` with a random port and exercise the
full HTTP stack against a real SQLite instance.

```bash
mvn test
```

There are seven tests covering creation, validation, list/filtering, the
`GET /books/{id}` 404 path, update, delete, and the health endpoint.

## Project layout

```
src/main/java/com/example/books/
  BooksApplication.java
  controller/BookController.java
  controller/HealthController.java
  exception/BookNotFoundException.java
  exception/ErrorResponse.java
  exception/GlobalExceptionHandler.java
  model/Book.java
  repository/BookRepository.java
src/main/resources/application.properties
src/test/java/com/example/books/BooksApiIntegrationTests.java
pom.xml
```
