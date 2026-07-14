import Database from "better-sqlite3";
import type { Database as DBType } from "better-sqlite3";
import { join } from "node:path";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export type NewBook = Pick<Book, "title" | "author" | "year" | "isbn">;
export type UpdateBook = Partial<NewBook>;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
`;

export function openDatabase(path: string = join(process.cwd(), "books.db")): DBType {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(SCHEMA);
  return db;
}

export function createBook(db: DBType, input: NewBook): Book {
  const stmt = db.prepare(
    `INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn)
     RETURNING *`
  );
  return stmt.get({
    title: input.title,
    author: input.author,
    year: input.year ?? null,
    isbn: input.isbn ?? null,
  }) as Book;
}

export function listBooks(db: DBType, author?: string): Book[] {
  if (author) {
    return db.prepare(`SELECT * FROM books WHERE author = ? ORDER BY id ASC`).all(author) as Book[];
  }
  return db.prepare(`SELECT * FROM books ORDER BY id ASC`).all() as Book[];
}

export function getBook(db: DBType, id: number): Book | undefined {
  return db.prepare(`SELECT * FROM books WHERE id = ?`).get(id) as Book | undefined;
}

export function updateBook(db: DBType, id: number, input: UpdateBook): Book | undefined {
  const existing = getBook(db, id);
  if (!existing) return undefined;

  const next = {
    title: input.title ?? existing.title,
    author: input.author ?? existing.author,
    year: input.year ?? existing.year,
    isbn: input.isbn ?? existing.isbn,
  };

  return db
    .prepare(
      `UPDATE books SET title = @title, author = @author, year = @year, isbn = @isbn,
       updated_at = datetime('now') WHERE id = @id RETURNING *`
    )
    .get({ id, ...next }) as Book;
}

export function deleteBook(db: DBType, id: number): boolean {
  const result = db.prepare(`DELETE FROM books WHERE id = ?`).run(id);
  return result.changes > 0;
}
