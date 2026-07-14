# Book Collection API

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation
- Health check endpoint
- SQLite database (embedded)

## Requirements

- Python 3.9+
- pip (Python package manager)

## Setup

1. Clone or download this repository.

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API

Start the server with:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Health Check
```
GET /health/
```
Returns API status and database connection status.

### Books

- `POST /books/` – Create a new book
- `GET /books/` – List all books (optional query param `?author=name` to filter)
- `GET /books/{id}` – Get a single book by ID
- `PUT /books/{id}` – Update a book
- `DELETE /books/{id}` – Delete a book

### Book Schema

All book endpoints expect or return JSON with the following fields:

| Field   | Type   | Required | Description                          |
|---------|--------|----------|--------------------------------------|
| title   | string | yes      | Book title (non-empty)              |
| author  | string | yes      | Author name (non-empty)             |
| year    | integer| no       | Publication year (1000–2100)        |
| isbn    | string | no       | ISBN (digits and hyphens only)      |

The response includes additional fields: `id`, `created_at`, `updated_at`.

### Example Requests

Create a book:
```bash
curl -X POST http://localhost:8000/books/ \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

List books:
```bash
curl http://localhost:8000/books/
```

Filter by author:
```bash
curl "http://localhost:8000/books/?author=Fitzgerald"
```

Get a single book:
```bash
curl http://localhost:8000/books/1
```

Update a book:
```bash
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

Delete a book:
```bash
curl -X DELETE http://localhost:8000/books/1
```

## Testing

Run the test suite:

```bash
python -m pytest app/tests/ -v
```

## Database

The API uses SQLite with a local file `books.db`. The database file is created automatically when the application starts (if it doesn't already exist).

## License

This project is provided for demonstration purposes.