# Books API

A REST API for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17+ (tested with Java 17 and 26)
- Maven 3.6+

## Setup & Run

From the project directory:

```bash
./mvnw spring-boot:run
# or, if Maven is installed globally:
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db`
is created automatically in the working directory on first run, and the
`books` table is created from `src/main/resources/schema.sql`.

## Endpoints

| Method   | Path          | Description                          |
|----------|---------------|--------------------------------------|
| `GET`    | `/health`     | Health check (`{"status":"UP"}`)     |
| `POST`   | `/books`      | Create a new book                    |
| `GET`    | `/books`      | List all books (supports `?author=`) |
| `GET`    | `/books/{id}` | Get a single book                    |
| `PUT`    | `/books/{id}` | Update a book                        |
| `DELETE` | `/books/{id}` | Delete a book                        |

### Book JSON shape

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Status codes

- `201 Created` — book created (on `POST`)
- `200 OK` — successful read / update / list
- `204 No Content` — successful delete
- `400 Bad Request` — validation error (missing title/author)
- `404 Not Found` — book with given id does not exist

## Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1966,"isbn":"ISBN-X"}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

The test suite includes:

- `BookApiIntegrationTest` — end-to-end tests over MockMvc covering the full
  create/list/get/update/delete flow, the `?author=` filter, the health
  endpoint, validation failures (missing title/author), and 404 handling.
  Uses an in-memory SQLite database (no files written to disk).
- `BookServiceTest` — unit tests for the service layer using a mocked
  repository, covering create, list (with and without author filter), update,
  delete, and the not-found case.

## Build a runnable jar

```bash
mvn clean package
java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

## Project layout

```
src/main/java/com/example/books/
    BooksApplication.java        # Spring Boot entry point
    Book.java                    # Book model with validation annotations
    BookRepository.java          # JDBC-based persistence (SQLite)
    BookService.java             # business logic
    BookController.java          # REST controller for /books
    HealthController.java        # /health endpoint
    BookNotFoundException.java   # 404 exception
src/main/resources/
    application.properties       # datasource config
    schema.sql                   # table creation script
src/test/java/com/example/books/
    BookApiIntegrationTest.java
    BookServiceTest.java
    JsonTestSupport.java
src/test/resources/
    application-test.properties  # in-memory SQLite config for tests
```
