# Book Collection API

A REST API service for managing a book collection, built with Java and Spring Boot,
storing data in an embedded SQLite database.

## Requirements

- Java 17+ (tested with Java 26)
- Maven 3.6+ (uses the included Maven Wrapper-free setup; install Maven or use your IDE's bundled Maven)

## Setup & Run

From the project root:

```bash
mvn clean spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite file `books.db` is created
in the working directory on first run.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check (`{"status":"UP"}`)     |
| POST   | `/books`        | Create a book (201)                  |
| GET    | `/books`        | List all books; supports `?author=`  |
| GET    | `/books/{id}`   | Get a single book (200 or 404)       |
| PUT    | `/books/{id}`   | Update a book (200 or 404)           |
| DELETE | `/books/{id}`   | Delete a book (204 or 404)           |

### Request body (POST/PUT)

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

`title` and `author` are required. `year` and `isbn` are optional. Invalid input
returns `400 Bad Request` with a JSON `errors` array describing the failing fields.

## Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}'

curl 'http://localhost:8080/books?author=tolkien'
curl http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

Tests are integration tests using Spring Boot's `MockMvc` against a SQLite-backed
JPA layer (profile `test`, database file under `target/`):

- `BookControllerIntegrationTest` — covers health check, create/get lifecycle,
  input validation, author filter, update, delete, and 404 handling.
- `BookRepositoryTest` — covers the `findByAuthorContainingIgnoreCase` query.

## Project layout

```
src/main/java/com/example/books
├── BookCollectionApplication.java
├── dto/   BookRequest.java, BookResponse.java
├── model/ Book.java
├── repository/ BookRepository.java
└── web/   BookController.java, HealthController.java
```
