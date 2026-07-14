# Book Collection REST API

A REST API service for managing a book collection built with TypeScript, Express, and SQLite.

## Features

- **CRUD Operations**: Create, read, update, and delete books
- **Filtering**: List books filtered by author
- **Input Validation**: Required fields and data type validation
- **Health Check**: API health monitoring endpoint
- **SQLite Storage**: Embedded database for data persistence

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/:id` | Get a single book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

## Book Schema

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:00:00.000Z"
}
```

## Setup and Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Build the project**:
   ```bash
   npm run build
   ```

3. **Run the application**:
   ```bash
   npm start
   ```

   The server will start on port 3000 (or the port specified in the `PORT` environment variable).

## Development

### Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Compile TypeScript to JavaScript
- `npm start` - Start the production server
- `npm test` - Run tests
- `npm test:watch` - Run tests in watch mode

### Environment Variables

- `PORT` - Server port (default: 3000)

### Testing

Run the test suite:
```bash
npm test
```

Run tests in watch mode:
```bash
npm test:watch
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "year": 1937,
    "isbn": "9780547928227"
  }'
```

### List all books
```bash
curl http://localhost:3000/books
```

### List books by author
```bash
curl "http://localhost:3000/books?author=J.R.R.+Tolkien"
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Hobbit, or There and Back Again"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Validation Rules

- **Title**: Required, non-empty string
- **Author**: Required, non-empty string
- **Year**: Optional, must be a valid positive number not in the future
- **ISBN**: Optional, must be unique if provided

## Error Responses

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `409` - Conflict (duplicate ISBN)
- `500` - Internal Server Error

Error responses include a JSON body with an `error` field describing the issue.

## Database

The application uses SQLite with the `better-sqlite3` library. The database file (`books.db`) is created automatically in the project root directory.

## License

ISC