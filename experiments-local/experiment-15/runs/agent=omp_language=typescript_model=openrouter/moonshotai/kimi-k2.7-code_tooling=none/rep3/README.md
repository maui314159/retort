# Book Collection API

A TypeScript/Express REST API for managing a book collection, backed by SQLite.

## Features

- `POST /books` — Create a new book
- `GET /books` — List all books (supports `?author=` filter)
- `GET /books/{id}` — Get a single book
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

## Prerequisites

- Node.js 20+
- npm

## Setup

```bash
npm install
```

## Run

Development:

```bash
npm run dev
```

Production build:

```bash
npm run build
npm start
```

The API runs on `http://localhost:3000` by default. Set `PORT` to override.

## Test

```bash
npm test
```

## Data storage

Books are stored in `books.sqlite` by default. Set `DATABASE_PATH` to use a different file.

## Example requests

Create a book:

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}'
```

List books:

```bash
curl http://localhost:3000/books
```

Filter by author:

```bash
curl 'http://localhost:3000/books?author=Tolkien'
```
