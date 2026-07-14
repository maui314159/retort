# Books API

A small REST API for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17+ (tested on Java 26)
- Maven 3.6+

## Setup & Run

```bash
mvn clean spring-boot:run
```

The service starts on `http://localhost:8080`. A `books.db` SQLite file is created
in the working directory on first run.

## Endpoints

| Method   | Path           | Description                         |
|----------|----------------|-------------------------------------|
| GET      | `/health`      | Health check                        |
| POST     | `/books`       | Create a book                       |
| GET      | `/books`       | List all books (`?author=` filter)  |
| GET      | `/books/{id}`  | Get one book                        |
| PUT      | `/books/{id}`  | Update a book                       |
| DELETE   | `/books/{id}`  | Delete a book                       |

### Book payload

```json
{
  "title": "Refactoring",
  "author": "Martin Fowler",
  "year": 1999,
  "isbn": "9780201485677"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Status codes

- `201 Created` on successful creation (Location header set)
- `200 OK` on successful read / update / list
- `204 No Content` on successful delete
- `400 Bad Request` on validation errors (JSON body with field-level `errors`)
- `404 Not Found` when a book id does not exist

## Examples

```bash
# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring","author":"Martin Fowler","year":1999,"isbn":"9780201485677"}'

# List
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Martin%20Fowler'

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Refactoring (2nd)","author":"Martin Fowler","year":2018,"isbn":"9780134757599"}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
mvn test
```

The test suite uses an in-memory SQLite database and covers:

- `HealthControllerTest` — health check endpoint
- `BookValidationTest` — input validation (title/author required)
- `BookCrudIntegrationTest` — full create/read/update/delete flow, author filter, 404 handling

## Build a jar

```bash
mvn clean package
java -jar target/books-api-0.0.1-SNAPSHOT.jar
```
