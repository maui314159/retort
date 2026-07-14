import Database from "better-sqlite3";

/** A configured better-sqlite3 database with the books schema applied. */
export type BooksDb = Database.Database;

const MIGRATION = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
`;

/** Open (or create) a SQLite database at the given path and apply the schema. */
export function openDatabase(path: string): BooksDb {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(MIGRATION);
  return db;
}

/** Open a fresh in-memory database. Useful for tests. */
export function openMemoryDatabase(): BooksDb {
  const db = new Database(":memory:");
  db.exec(MIGRATION);
  return db;
}

/** Close the database safely. */
export function closeDatabase(db: BooksDb): void {
  db.close();
}
