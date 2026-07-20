import { DatabaseSync } from "node:sqlite";
import type { Book, BookInput } from "./types.ts";

interface BookRow {
  id: number | bigint;
  title: string;
  author: string;
  year: number | bigint | null;
  isbn: string | null;
}

/** Open (or create) the SQLite database at `path` and ensure the schema exists. */
export function createDatabase(path: string): DatabaseSync {
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    )
  `);
  return db;
}

function rowToBook(row: BookRow): Book {
  return {
    id: Number(row.id),
    title: row.title,
    author: row.author,
    year: row.year === null ? null : Number(row.year),
    isbn: row.isbn,
  };
}

export function createBook(db: DatabaseSync, input: BookInput): Book {
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
  );
  const result = stmt.run(input.title, input.author, input.year, input.isbn);
  const id = Number(result.lastInsertRowid);
  const book = getBook(db, id);
  if (book === null) {
    throw new Error(`Failed to read back book with id ${id}`);
  }
  return book;
}

/** List all books, optionally filtered by exact author name. */
export function listBooks(db: DatabaseSync, author?: string): Book[] {
  if (author !== undefined) {
    const stmt = db.prepare(
      "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
    );
    return (stmt.all(author) as unknown as BookRow[]).map(rowToBook);
  }
  const stmt = db.prepare(
    "SELECT id, title, author, year, isbn FROM books ORDER BY id",
  );
  return (stmt.all() as unknown as BookRow[]).map(rowToBook);
}

export function getBook(db: DatabaseSync, id: number): Book | null {
  const stmt = db.prepare(
    "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
  );
  const row = stmt.get(id) as unknown as BookRow | undefined;
  return row === undefined ? null : rowToBook(row);
}

/** Replace a book's fields. Returns the updated book, or null if it does not exist. */
export function updateBook(
  db: DatabaseSync,
  id: number,
  input: BookInput,
): Book | null {
  const stmt = db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
  );
  const result = stmt.run(input.title, input.author, input.year, input.isbn, id);
  if (result.changes === 0) {
    return null;
  }
  return getBook(db, id);
}

/** Delete a book. Returns true if a row was removed. */
export function deleteBook(db: DatabaseSync, id: number): boolean {
  const stmt = db.prepare("DELETE FROM books WHERE id = ?");
  const result = stmt.run(id);
  return result.changes > 0;
}
