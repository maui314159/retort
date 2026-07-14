import Database from "better-sqlite3";
import type { Database as SqliteDb } from "better-sqlite3";

export interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

const CREATE_TABLE = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT
);
`;

export function createDb(dbPath: string): SqliteDb {
  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.exec(CREATE_TABLE);
  return db;
}

export function createMemoryDb(): SqliteDb {
  const db = new Database(":memory:");
  db.exec(CREATE_TABLE);
  return db;
}
