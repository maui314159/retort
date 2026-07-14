# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite.

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

The server starts on port 3000 (override with the `PORT` environment variable).

## Endpoints

| Method  | Path          | Description                    |
|---------|---------------|--------------------------------|
| GET     | /health       | Health check                   |
| POST    | /books        | Create a new book              |
| GET     | /books        | List all books (?author=filter)|
| GET     | /books/:id    | Get a book by ID               |
| PUT     | /books/:id    | Update a book                  |
| DELETE  | /books/:id    | Delete a book                  |

### Book fields

| Field  | Required | Type   |
|--------|----------|--------|
| title  | yes      | string |
| author | yes      | string |
| year   | no       | number |
| isbn   | no       | string |

## Test

```bash
npm test
```
