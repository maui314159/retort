import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

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

export function openDatabase(path: string): DatabaseType {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
  return db;
}

export function createBook(db: DatabaseType, input: BookInput): Book {
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const result = stmt.run(
    input.title,
    input.author,
    input.year ?? null,
    input.isbn ?? null
  );
  return getBook(db, Number(result.lastInsertRowid)) as Book;
}

export function getBook(db: DatabaseType, id: number): Book | undefined {
  const stmt = db.prepare("SELECT * FROM books WHERE id = ?");
  return stmt.get(id) as Book | undefined;
}

export function listBooks(db: DatabaseType, author?: string): Book[] {
  if (author) {
    const stmt = db.prepare("SELECT * FROM books WHERE author = ? ORDER BY id");
    return stmt.all(author) as Book[];
  }
  const stmt = db.prepare("SELECT * FROM books ORDER BY id");
  return stmt.all() as Book[];
}

export function updateBook(
  db: DatabaseType,
  id: number,
  input: Partial<BookInput>
): Book | undefined {
  const existing = getBook(db, id);
  if (!existing) return undefined;
  const title = input.title ?? existing.title;
  const author = input.author ?? existing.author;
  const year = input.year ?? existing.year;
  const isbn = input.isbn ?? existing.isbn;
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(title, author, year, isbn, id);
  return getBook(db, id);
}

export function deleteBook(db: DatabaseType, id: number): boolean {
  const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return result.changes > 0;
}
