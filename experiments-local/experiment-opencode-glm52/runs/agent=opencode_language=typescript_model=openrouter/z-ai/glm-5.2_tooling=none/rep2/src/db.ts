import Database from "better-sqlite3";
import type { Database as DBType } from "better-sqlite3";

export type { DBType };

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function createDb(file: string = ":memory:"): DBType {
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
  return db;
}

export type NewBook = Omit<Book, "id">;
