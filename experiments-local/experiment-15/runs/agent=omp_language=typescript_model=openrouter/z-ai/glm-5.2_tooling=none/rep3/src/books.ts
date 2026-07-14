import type Database from "better-sqlite3";

// Domain entities owned by this module. Named types only — no ReturnType helpers.

/** A book record as stored in SQLite and returned to clients. */
export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  createdAt: string;
}

/** Payload accepted by POST /books. title and author are required. */
export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

/** Partial payload accepted by PUT /books/{id}. Only the supplied fields change. */
export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}

/** Raw row shape read from SQLite before mapping to {@link Book}. */
interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
}

function mapRow(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    createdAt: row.created_at,
  };
}

/** Insert a book and return the stored record. Throws on constraint violations. */
export function createBook(db: Database.Database, input: BookInput): Book {
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const info = stmt.run(
    input.title,
    input.author,
    input.year ?? null,
    input.isbn ?? null
  );
  return getBook(db, Number(info.lastInsertRowid)) as Book;
}

/** List books, optionally filtered by exact author name. */
export function listBooks(db: Database.Database, author?: string): Book[] {
  if (author === undefined || author === "") {
    const rows = db.prepare("SELECT * FROM books ORDER BY id ASC").all() as BookRow[];
    return rows.map(mapRow);
  }
  const rows = db
    .prepare("SELECT * FROM books WHERE author = ? ORDER BY id ASC")
    .all(author) as BookRow[];
  return rows.map(mapRow);
}

/** Return a single book or null if missing. */
export function getBook(db: Database.Database, id: number): Book | null {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | BookRow
    | undefined;
  return row ? mapRow(row) : null;
}

/** Apply a partial update. Returns the updated book or null if the id does not exist. */
export function updateBook(
  db: Database.Database,
  id: number,
  update: BookUpdate
): Book | null {
  const existing = getBook(db, id);
  if (!existing) return null;
  const next: Book = {
    id: existing.id,
    title: update.title ?? existing.title,
    author: update.author ?? existing.author,
    year: update.year !== undefined ? update.year : existing.year,
    isbn: update.isbn !== undefined ? update.isbn : existing.isbn,
    createdAt: existing.createdAt,
  };
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(next.title, next.author, next.year, next.isbn, next.id);
  return getBook(db, id);
}

/** Delete a book. Returns true if a row was removed, false otherwise. */
export function deleteBook(db: Database.Database, id: number): boolean {
  const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return info.changes > 0;
}
