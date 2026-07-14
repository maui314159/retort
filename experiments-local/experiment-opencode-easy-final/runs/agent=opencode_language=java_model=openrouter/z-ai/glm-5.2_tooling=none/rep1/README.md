# Book Collection REST API

A small REST API for managing a book collection, built with **Javalin**, **SQLite**, and **Java 21+**.

## Requirements

- Java 21 or newer
- Maven 3.8+

## Setup & Run

```bash
mvn clean package
java -jar target/book-api-1.0.0.jar
```

The server starts on port `7000` (override with the `PORT` env var). The SQLite
database file defaults to `books.db` in the working directory (override with the
`DB_PATH` env var).

```bash
PORT=8080 DB_PATH=/tmp/books.db java -jar target/book-api-1.0.0.jar
```

### Run directly with Maven (no packaging)

```bash
mvn compile exec:java -Dexec.mainClass=com.example.books.Main
```

## Endpoints

| Method | Path            | Description                       |
|--------|-----------------|-----------------------------------|
| GET    | `/health`       | Health check (`{"status":"ok"}`)  |
| POST   | `/books`        | Create a book                     |
| GET    | `/books`        | List books (supports `?author=`)  |
| GET    | `/books/{id}`   | Get a single book                 |
| PUT    | `/books/{id}`   | Update a book                     |
| DELETE | `/books/{id}`   | Delete a book                     |

### Book payload

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780261102217"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (JSON body `{"error":"..."}`)
- `404 Not Found` — book does not exist
- `500 Internal Server Error` — unexpected error

## Examples

```bash
curl -X POST http://localhost:7000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261102217"}'

curl http://localhost:7000/books?author=J.R.R.%20Tolkien
curl http://localhost:7000/books/1
curl -X DELETE http://localhost:7000/books/1
```

## Tests

```bash
mvn test
```

The integration tests boot the full Javalin app against a temporary SQLite
database and exercise every endpoint (health, create, list+filter, update,
delete, 404 paths, validation failures).
