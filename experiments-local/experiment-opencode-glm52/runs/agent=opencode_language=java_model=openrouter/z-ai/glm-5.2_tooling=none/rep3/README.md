# Books API

A small REST API for managing a book collection, built with **Spring Boot 3.4** and **SQLite** (via the `sqlite-jdbc` driver and Spring `JdbcTemplate`). Data is stored in a local file-based SQLite database (`books.db`).

## Endpoints

| Method  | Path          | Description                              |
|---------|---------------|------------------------------------------|
| GET     | `/health`     | Health check (`{"status":"UP"}`)         |
| POST    | `/books`      | Create a new book (returns `201 Created`)|
| GET     | `/books`      | List all books (supports `?author=`)     |
| GET     | `/books/{id}` | Get a single book (`404` if missing)     |
| PUT     | `/books/{id}` | Update a book (`404` if missing)         |
| DELETE  | `/books/{id}` | Delete a book (`204`, `404` if missing)  |

### Book JSON shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

### Validation

- `title` and `author` are **required** (non-blank).
- `title` ≤ 500 chars, `author` ≤ 200 chars, `isbn` ≤ 32 chars.
- Invalid input returns `400 Bad Request` with a JSON error body.

## Requirements

- JDK 17+ (built/tested on OpenJDK 17–26)
- Maven 3.6+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The server starts on `http://localhost:8080`. A `books.db` file is created in the working directory on first run; the schema is initialized automatically from `src/main/resources/schema.sql`.

## Example requests

```bash
# Create a book
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List all
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get / update / delete
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

The suite includes:

- `BookRepositoryTest` — JDBC persistence, filtering, update/delete.
- `BookApiIntegrationTest` — end-to-end HTTP lifecycle via MockMvc (create, get, list, filter, update, delete, 404s, validation).
- `BookRequestValidationTest` — bean-validation rules for the request DTO.

Tests run against an in-memory SQLite database (`jdbc:sqlite::memory:`).
