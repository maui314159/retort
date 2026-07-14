# Books API

A small REST API for managing a book collection, built with **Spring Boot 3**, **SQLite** (via `sqlite-jdbc` and Hibernate's community SQLite dialect), and bean validation.

## Endpoints

| Method | Path             | Description                              |
|--------|------------------|------------------------------------------|
| GET    | `/health`        | Health check (`{"status":"UP"}`)         |
| POST   | `/books`         | Create a new book (title, author, year, isbn) |
| GET    | `/books`         | List all books, optional `?author=` filter |
| GET    | `/books/{id}`    | Get a single book by ID                  |
| PUT    | `/books/{id}`    | Update a book                            |
| DELETE | `/books/{id}`    | Delete a book                            |

### Validation

`title` and `author` are required. If either is missing or blank on a `POST`/`PUT`, the API responds with `400 Bad Request` and a body describing the field errors.

### Status codes

- `201 Created` — on successful `POST`
- `200 OK` — on successful `GET` / `PUT`
- `204 No Content` — on successful `DELETE`
- `400 Bad Request` — validation failure
- `404 Not Found` — book does not exist

## Requirements

- Java 17+ (built/tested on Java 26)
- Maven 3.6+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

The service starts on `http://localhost:8080`. SQLite data is persisted in `books.db` in the working directory.

## Tests

```bash
mvn test
```

Tests use Spring Boot's `MockMvc` against an in-memory H2 database (via `application-test.properties`), covering:

1. Creating a book returns `201` with the created body.
2. Validation rejects missing `title`/`author` with `400`.
3. Listing books returns all entries and supports `?author=` filtering (case-insensitive).
4. Getting/updating/deleting a non-existent book returns `404`.
5. `DELETE` returns `204` and then `404` on repeat.
6. `/health` returns `200` with `{"status":"UP"}`.

## Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261103283"}'

curl http://localhost:8080/books?author=j.r.r.%20tolkien
```
