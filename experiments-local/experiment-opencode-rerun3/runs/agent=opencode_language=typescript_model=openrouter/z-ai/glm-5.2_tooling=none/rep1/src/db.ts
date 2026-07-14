import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";

export interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export type DB = Database.Database;

export function openDb(file: string): DB {
  let db: DB;
  if (file === ":memory:") {
    db = new Database(":memory:");
  } else {
    const dir = path.dirname(file);
    if (dir && dir !== "." && !fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    db = new Database(file);
    try {
      db.pragma("journal_mode = WAL");
    } catch {
      // WAL not available in this context; ignore.
    }
  }
  db.pragma("foreign_keys = ON");
  migrate(db);
  return db;
}

export function migrate(db: DB): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
}

export function closeDb(db: DB): void {
  try {
    db.close();
  } catch {
    // already closed
  }
}
