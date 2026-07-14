import Database, { type Database as DatabaseType } from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";

export type Db = DatabaseType;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  title      TEXT    NOT NULL,
  author     TEXT    NOT NULL,
  year       INTEGER,
  isbn       TEXT,
  created_at TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`;

export function openDatabase(file: string): Db {
  if (file !== ":memory:") {
    const dir = path.dirname(file);
    if (dir && dir !== "" && dir !== ".") {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(SCHEMA);
  return db;
}
