import { createRequire } from "node:module";
import type { DatabaseSync as DatabaseSyncType } from "node:sqlite";

const require = createRequire(import.meta.url);
const { DatabaseSync } = require("node:sqlite") as {
  DatabaseSync: typeof DatabaseSyncType;
};

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: unknown;
  author: unknown;
  year: unknown;
  isbn: unknown;
}

export interface ValidationError {
  field: string;
  message: string;
}

export function validateBook(input: BookInput): ValidationError[] {
  const errors: ValidationError[] = [];

  if (typeof input.title !== "string" || input.title.trim() === "") {
    errors.push({ field: "title", message: "title is required and must be a non-empty string" });
  }

  if (typeof input.author !== "string" || input.author.trim() === "") {
    errors.push({ field: "author", message: "author is required and must be a non-empty string" });
  }

  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== "number" || !Number.isFinite(input.year) || input.year < 0 || !Number.isInteger(input.year)) {
      errors.push({ field: "year", message: "year must be a non-negative integer" });
    }
  }

  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string" || input.isbn.trim() === "") {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string when provided" });
    }
  }

  return errors;
}

export type DB = DatabaseSyncType;

export function initDb(path: string = ":memory:"): DB {
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return db;
}

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function rowToBook(row: BookRow | undefined): Book | null {
  if (!row) return null;
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
  };
}

export function createBook(db: DB, input: BookInput): Book {
  const errors = validateBook(input);
  if (errors.length > 0) {
    const err = new Error("Validation failed") as Error & { status?: number; errors?: ValidationError[] };
    err.status = 400;
    err.errors = errors;
    throw err;
  }

  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const year = input.year === undefined ? null : (input.year as number);
  const isbn = input.isbn === undefined || input.isbn === null ? null : (input.isbn as string);
  const info = stmt.run(input.title as string, input.author as string, year, isbn);
  const book = getBook(db, Number(info.lastInsertRowid));
  if (!book) throw new Error("Failed to retrieve created book");
  return book;
}

export function listBooks(db: DB, authorFilter?: string): Book[] {
  let rows: BookRow[];
  if (authorFilter && authorFilter.trim() !== "") {
    rows = db.prepare("SELECT * FROM books WHERE author = ? ORDER BY id").all(authorFilter) as unknown as BookRow[];
  } else {
    rows = db.prepare("SELECT * FROM books ORDER BY id").all() as unknown as BookRow[];
  }
  return rows.map((r) => rowToBook(r) as Book);
}

export function getBook(db: DB, id: number): Book | null {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as BookRow | undefined;
  return rowToBook(row);
}

export function updateBook(db: DB, id: number, input: Partial<BookInput>): Book {
  const existing = getBook(db, id);
  if (!existing) {
    const err = new Error("Book not found") as Error & { status?: number };
    err.status = 404;
    throw err;
  }

  const merged: BookInput = {
    title: input.title !== undefined ? input.title : existing.title,
    author: input.author !== undefined ? input.author : existing.author,
    year: input.year !== undefined ? input.year : existing.year,
    isbn: input.isbn !== undefined ? input.isbn : existing.isbn,
  };

  const errors = validateBook(merged);
  if (errors.length > 0) {
    const err = new Error("Validation failed") as Error & { status?: number; errors?: ValidationError[] };
    err.status = 400;
    err.errors = errors;
    throw err;
  }

  const year = merged.year === undefined || merged.year === null ? null : (merged.year as number);
  const isbn = merged.isbn === undefined || merged.isbn === null ? null : (merged.isbn as string);
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(merged.title as string, merged.author as string, year, isbn, id);

  return getBook(db, id) as Book;
}

export function deleteBook(db: DB, id: number): boolean {
  const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return info.changes > 0;
}
