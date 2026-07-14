# Book Collection REST API

A FastAPI-based REST API service for managing a book collection with SQLite database.

## Features

- **POST /books** - Create a new book with title, author, year, and ISBN
- **GET /books** - List all books with optional author filter
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint
- Input validation for required fields
- JSON responses with appropriate HTTP status codes

## Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Run the application:**

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Endpoints

### Health Check
```
GET /health
```
Returns: `{"status": "healthy"}`

### Create a Book
```
POST /books
```
Request body:
```json
{
  "title": "string",
  "author": "string",
  "year": "integer (optional)",
  "isbn": "string (optional)"
}
```
Returns: `201 Created` with book data including generated ID

### List Books
```
GET /books
```
Optional query parameter: `?author=name` (case-insensitive partial match)

Returns: `200 OK` with array of books

### Get Single Book
```
GET /books/{id}
```
Returns: `200 OK` with book data or `404 Not Found`

### Update Book
```
PUT /books/{id}
```
Request body (partial updates supported):
```json
{
  "title": "string (optional)",
  "author": "string (optional)",
  "year": "integer (optional)",
  "isbn": "string (optional)"
}
```
Returns: `200 OK` with updated book data or `404 Not Found`

### Delete Book
```
DELETE /books/{id}
```
Returns: `204 No Content` or `404 Not Found`

## Validation Rules

- `title`: Required, 1-200 characters
- `author`: Required, 1-100 characters
- `year`: Optional, between 1000-2100
- `isbn`: Optional, 10-13 characters

## Database

The application uses SQLite with a database file at `./books.db`. The database is automatically created when the application starts.

## Testing

Run the test suite:

```bash
pytest test_api.py -v
```

Tests include:
- Health check endpoint
- Book creation with validation
- Listing books with filtering
- Getting, updating, and deleting books
- Error handling for non-existent books

## Project Structure

```
.
├── main.py              # FastAPI application and database setup
├── test_api.py          # Unit and integration tests
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── books.db            # SQLite database (created on first run)
```