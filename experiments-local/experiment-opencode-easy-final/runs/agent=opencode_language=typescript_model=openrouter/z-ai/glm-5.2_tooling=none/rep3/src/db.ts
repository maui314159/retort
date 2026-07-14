import Database from "better-sqlite3";
import type { Database as DBType } from "better-sqlite3";
import path from "node:path";

export interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

let dbInstance: DBType | null = null;

export function getDb(dbPath?: string): DBType {
  if (dbInstance && dbInstance.open) {
    return dbInstance;
  }
  const location = dbPath ?? process.env.DB_PATH ?? path.join(process.cwd(), "books.db");
  dbInstance = new Database(location);
  dbInstance.pragma("journal_mode = WAL");
  migrate(dbInstance);
  return dbInstance;
}

export function closeDb(): void {
  if (dbInstance && dbInstance.open) {
    dbInstance.close();
  }
  dbInstance = null;
}

export function resetDbForTesting(dbPath: string): DBType {
  closeDb();
  dbInstance = new Database(dbPath);
  dbInstance.pragma("journal_mode = WAL");
  migrate(dbInstance);
  return dbInstance;
}

function migrate(db: DBType): void {
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
