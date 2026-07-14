import Database from "better-sqlite3";
import type { Database as DB } from "better-sqlite3";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export function openDatabase(path: string): DB {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
  `);
  return db;
}

export function rowToBook(row: Record<string, unknown>): Book {
  return {
    id: Number(row.id),
    title: String(row.title),
    author: String(row.author),
    year: row.year === null ? null : Number(row.year),
    isbn: row.isbn === null ? null : String(row.isbn),
    created_at: String(row.created_at),
    updated_at: String(row.updated_at),
  };
}
