# books-api

A small REST API service for managing a book collection, written in Java with Spring Boot and SQLite.

## Endpoints

| Method | Path              | Description                                      |
|--------|-------------------|--------------------------------------------------|
| GET    | `/health`         | Health check (returns `{"status":"UP"}`)          |
| POST   | `/books`          | Create a new book (title, author, year, isbn)      |
| GET    | `/books`          | List all books; supports `?author=` filter        |
| GET    | `/books/{id}`     | Get a single book by ID                            |
| PUT    | `/books/{id}`     | Update a book (partial update of year/isbn; title/author required) |
| DELETE | `/books/{id}`     | Delete a book                                      |

### Book JSON shape

```json
{ "id": 1, "title": "Refactoring", "author": "Fowler", "year": 1999, "isbn": "9780201485677" }
```

## Validation rules

- `title` is required (non-blank)
- `author` is required (non-blank)
- `year`, if provided, must be between 0 and 9999
- `isbn` is optional

Validation errors return HTTP `400` with a JSON body:
```json
{ "status": 400, "error": "Bad Request", "message": "title is required" }
```

Missing books return HTTP `404` with a similar body.

## Storage

Data is stored in SQLite. By default a file-based database `books.db` is created in the working directory. The location can be overridden with the `BOOKS_DB_URL` environment variable:

```bash
BOOKS_DB_URL=jdbc:sqlite:/tmp/books.db mvn spring-boot:run
```

The `books` table is created automatically on startup if it does not exist.

## Requirements

- Java 17 or newer (built and tested on Java 17–26)
- Maven 3.6+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
# or after packaging:
java -jar target/books-api-1.0.0.jar
```

The server listens on `http://localhost:8080`.

## Tests

```bash
mvn test
```

The test suite is an integration test (`BookIntegrationTests`) that boots the full Spring context against an in-memory SQLite database and exercises the HTTP endpoints with `WebTestClient`. Six test methods cover:

- the `/health` endpoint
- the full create / list / get / update / delete lifecycle
- input validation (missing `title` and missing `author`)
- the `?author=` filter on `GET /books`
- deleting a non-existent book returns `404`

## Example session

```bash
curl -X POST http://localhost:8080/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Refactoring","author":"Fowler","year":1999,"isbn":"9780201485677"}'

curl http://localhost:8080/books
curl http://localhost:8080/books?author=Fowler
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"Refactoring (2nd)","author":"Fowler","year":2008,"isbn":"9780134757599"}'
curl -X DELETE http://localhost:8080/books/1
```
