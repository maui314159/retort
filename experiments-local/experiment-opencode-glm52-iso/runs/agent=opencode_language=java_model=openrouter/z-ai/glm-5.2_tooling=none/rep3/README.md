# Books API

A REST API service for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17+ (built and tested on Java 26)
- Maven 3.6+

## Setup & Run

```bash
./mvnw spring-boot:run
# or, if Maven is installed globally:
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. A SQLite database file `books.db`
is created in the project root on first run.

## Endpoints

| Method   | Path           | Description                                  |
|----------|----------------|----------------------------------------------|
| `GET`    | `/health`      | Health check (`{"status":"UP"}`)             |
| `POST`   | `/books`       | Create a book (title, author, year, isbn)    |
| `GET`    | `/books`       | List all books; supports `?author=` filter   |
| `GET`    | `/books/{id}`  | Get a single book by ID                      |
| `PUT`    | `/books/{id}`  | Update a book                                |
| `DELETE` | `/books/{id}`  | Delete a book                                |

### Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261103283"}'

curl http://localhost:8080/books?author=tolkien
```

### Validation

- `title` and `author` are required (non-blank).
- `year`, when provided, must be a non-negative integer.
- Validation errors return `400 Bad Request` with a JSON body listing field errors.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error
- `404 Not Found` — resource not found

## Tests

```bash
mvn test
```

Integration tests use Spring Boot's `MockMvc` with an in-memory SQLite database
(`jdbc:sqlite:file:testdb?mode=memory&cache=shared`) and cover:

1. The `/health` endpoint.
2. The full create / list / filter / get / update / delete lifecycle.
3. Input validation (missing `title` and `author`).
4. `404` responses for unknown IDs on GET, PUT, and DELETE.
