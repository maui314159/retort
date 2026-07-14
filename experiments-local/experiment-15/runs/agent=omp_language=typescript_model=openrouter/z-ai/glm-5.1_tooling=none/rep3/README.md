# Book Collection API

A REST API for managing a book collection, built with Express and SQLite.

## Setup

```bash
npm install
```

## Run

```bash
# Production
npm run build
npm start

# Development
npm run dev
```

The server starts on port 3000 (override with the `PORT` environment variable).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/:id` | Get a book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

### Book fields

| Field | Required | Type |
|-------|----------|------|
| title | yes | string |
| author | yes | string |
| year | no | integer |
| isbn | no | string |

## Test

```bash
npm test
```
