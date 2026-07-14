import Database from "better-sqlite3";
import type { Database as DB } from "better-sqlite3";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT
);
`;

export function openDatabase(path: string): DB {
  if (path !== ":memory:") {
    mkdirSync(dirname(path), { recursive: true });
  }
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(SCHEMA);
  return db;
}

export function createBook(db: DB, input: BookInput): Book {
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

export function listBooks(db: DB, author?: string): Book[] {
  if (author) {
    return db
      .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
      .all(author) as Book[];
  }
  return db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
}

export function getBook(db: DB, id: number): Book | undefined {
  return db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | Book
    | undefined;
}

export function updateBook(
  db: DB,
  id: number,
  input: Partial<BookInput>
): Book | undefined {
  const existing = getBook(db, id);
  if (!existing) return undefined;
  const next: Book = {
    ...existing,
    title: input.title ?? existing.title,
    author: input.author ?? existing.author,
    year: input.year ?? existing.year,
    isbn: input.isbn ?? existing.isbn,
  };
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(next.title, next.author, next.year, next.isbn, id);
  return getBook(db, id);
}

export function deleteBook(db: DB, id: number): boolean {
  const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return info.changes > 0;
}
