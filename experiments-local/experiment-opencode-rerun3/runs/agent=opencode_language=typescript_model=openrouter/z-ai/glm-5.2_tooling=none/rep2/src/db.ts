import Database from "better-sqlite3";
import { randomUUID } from "crypto";

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

export function createDb(path: string = ":memory:"): Database.Database {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return db;
}

export type ValidationError = { field: string; message: string };

export function validateBook(input: BookInput): ValidationError[] {
  const errors: ValidationError[] = [];

  if (
    typeof input.title !== "string" ||
    input.title.trim().length === 0
  ) {
    errors.push({ field: "title", message: "title is required" });
  }

  if (
    typeof input.author !== "string" ||
    input.author.trim().length === 0
  ) {
    errors.push({ field: "author", message: "author is required" });
  }

  if (
    input.year !== undefined &&
    input.year !== null
  ) {
    if (
      typeof input.year !== "number" ||
      !Number.isInteger(input.year) ||
      input.year < 0
    ) {
      errors.push({ field: "year", message: "year must be a non-negative integer" });
    }
  }

  if (
    input.isbn !== undefined &&
    input.isbn !== null
  ) {
    if (typeof input.isbn !== "string") {
      errors.push({ field: "isbn", message: "isbn must be a string" });
    }
  }

  return errors;
}

function coerce(input: BookInput): Omit<Book, "id"> {
  return {
    title: (input.title as string).trim(),
    author: (input.author as string).trim(),
    year:
      input.year === undefined || input.year === null
        ? null
        : (input.year as number),
    isbn:
      input.isbn === undefined || input.isbn === null
        ? null
        : (input.isbn as string),
  };
}

export function listBooks(
  db: Database.Database,
  author?: string
): Book[] {
  if (author) {
    return db
      .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
      .all(author) as Book[];
  }
  return db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
}

export function getBook(db: Database.Database, id: string): Book | null {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | Book
    | undefined;
  return row ?? null;
}

export function createBook(db: Database.Database, input: BookInput): Book {
  const data = coerce(input);
  const id = randomUUID();
  db.prepare(
    "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
  ).run(id, data.title, data.author, data.year, data.isbn);
  return { id, ...data };
}

export function updateBook(
  db: Database.Database,
  id: string,
  input: BookInput
): Book | null {
  const existing = getBook(db, id);
  if (!existing) return null;

  const data = coerce(input);
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(data.title, data.author, data.year, data.isbn, id);
  return { id, ...data };
}

export function deleteBook(db: Database.Database, id: string): boolean {
  const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return result.changes > 0;
}
