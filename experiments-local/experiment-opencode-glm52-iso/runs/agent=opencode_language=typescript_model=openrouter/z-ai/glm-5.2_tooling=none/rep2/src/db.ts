import Database from "better-sqlite3";
import path from "path";

export type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

const DB_PATH =
  process.env.BOOK_DB_PATH || path.join(process.cwd(), "books.db");

let dbInstance: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!dbInstance) {
    dbInstance = new Database(DB_PATH);
    dbInstance.pragma("journal_mode = WAL");
    initSchema(dbInstance);
  }
  return dbInstance;
}

export function resetDb(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

export function initSchema(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
}

export type NewBook = Omit<Book, "id">;
