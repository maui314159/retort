import Database from "better-sqlite3";
import path from "path";

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
  year?: number;
  isbn?: string;
}

let dbInstance: Database.Database | null = null;

/**
 * Initialize (or return existing) SQLite database connection.
 * If `dbPath` is omitted, defaults to books.db in the cwd.
 * Pass ":memory:" to use an in-memory database (useful for tests).
 */
export function getDb(dbPath?: string): Database.Database {
  if (dbInstance && (!dbPath || dbPath === ":memory:")) {
    return dbInstance;
  }

  const dbPathToUse = dbPath ?? path.join(process.cwd(), "books.db");
  const db = new Database(dbPathToUse);

  db.pragma("journal_mode = WAL");

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);

  dbInstance = db;
  return db;
}

/**
 * Reset the database singleton — primarily for testing so each test
 * suite can get a fresh in-memory database.
 */
export function resetDb(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

/**
 * Return the currently active DB instance, initializing one if needed.
 */
export function currentDb(): Database.Database {
  return dbInstance ?? getDb();
}
