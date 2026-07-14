import Database from "better-sqlite3";
import type { BookInput, BookRecord } from "./types.js";

export interface DB {
  prepare(sql: string): PrepareResult;
  exec(sql: string): void;
  close(): void;
  pragma(s: string): unknown;
}

export interface PrepareResult {
  all(...params: unknown[]): unknown[];
  get(...params: unknown[]): unknown;
  run(...params: unknown[]): RunResult;
}

export interface RunResult {
  lastInsertRowid: number | bigint;
  changes: number;
}

export const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  title   TEXT NOT NULL,
  author  TEXT NOT NULL,
  year    INTEGER,
  isbn    TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
`;

export function openDatabase(path: string): Database.Database {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(SCHEMA);
  return db;
}

export function createBook(
  db: Database.Database,
  input: BookInput
): BookRecord {
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const result = stmt.run(input.title, input.author, input.year ?? null, input.isbn ?? null);
  const id = Number(result.lastInsertRowid);
  return getBook(db, id) as BookRecord;
}

export function updateBook(
  db: Database.Database,
  id: number,
  input: Partial<BookInput>
): BookRecord | undefined {
  const existing = getBook(db, id);
  if (!existing) return undefined;
  const merged: BookInput = {
    title: input.title ?? existing.title,
    author: input.author ?? existing.author,
    year: input.year ?? existing.year,
    isbn: input.isbn ?? existing.isbn,
  };
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now') WHERE id = ?"
  ).run(merged.title, merged.author, merged.year ?? null, merged.isbn ?? null, id);
  return getBook(db, id);
}

export function getBook(db: Database.Database, id: number): BookRecord | undefined {
  const stmt = db.prepare("SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?");
  return stmt.get(id) as BookRecord | undefined;
}

export function listBooks(db: Database.Database, author?: string): BookRecord[] {
  if (author) {
    return db
      .prepare("SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ? ORDER BY id")
      .all(author) as BookRecord[];
  }
  return db
    .prepare("SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id")
    .all() as BookRecord[];
}

export function deleteBook(db: Database.Database, id: number): boolean {
  const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return result.changes > 0;
}
