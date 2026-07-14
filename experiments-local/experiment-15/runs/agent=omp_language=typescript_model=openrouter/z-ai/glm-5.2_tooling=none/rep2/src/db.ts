import { Database } from "bun:sqlite";
import type { Book, BookInput } from "./types.ts";

export interface BookStore {
  list(author?: string): Book[];
  get(id: number): Book | null;
  create(input: BookInput): Book;
  update(id: number, input: BookInput): Book | null;
  delete(id: number): boolean;
  close(): void;
}

type Normalized = { title: string; author: string; year: number | null; isbn: string | null };

export function createBookStore(dbPath: string | ":memory:"): BookStore {
  const db = new Database(dbPath, { create: true });
  db.exec("PRAGMA journal_mode = WAL;");
  db.exec("PRAGMA foreign_keys = ON;");

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
  `);

  const stmtList = db.prepare<Book, [string | null]>(
    "SELECT id, title, author, year, isbn FROM books WHERE ?1 IS NULL OR author = ?1 ORDER BY id"
  );
  const stmtGet = db.prepare<Book, [number]>(
    "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
  );
  const stmtCreate = db.prepare<Book, [string, string, number | null, string | null]>(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn"
  );
  const stmtUpdate = db.prepare<Book, [string, string, number | null, string | null, number]>(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id, title, author, year, isbn"
  );
  const stmtDelete = db.prepare<{ id: number }, [number]>(
    "DELETE FROM books WHERE id = ? RETURNING id"
  );

  function normalize(input: BookInput): Normalized {
    return {
      title: String(input.title).trim(),
      author: String(input.author).trim(),
      year: input.year === undefined || input.year === null ? null : Number(input.year),
      isbn: input.isbn === undefined || input.isbn === null ? null : String(input.isbn).trim(),
    };
  }

  function mergeUpdate(existing: Book, input: BookInput): Normalized {
    return {
      title: input.title === undefined ? existing.title : String(input.title).trim(),
      author: input.author === undefined ? existing.author : String(input.author).trim(),
      year: input.year === undefined ? existing.year : input.year === null ? null : Number(input.year),
      isbn: input.isbn === undefined ? existing.isbn : input.isbn === null ? null : String(input.isbn).trim(),
    };
  }

  return {
    list(author?: string): Book[] {
      return stmtList.all(author ?? null);
    },
    get(id: number): Book | null {
      return stmtGet.get(id) ?? null;
    },
    create(input: BookInput): Book {
      const n = normalize(input);
      return stmtCreate.get(n.title, n.author, n.year, n.isbn)!;
    },
    update(id: number, input: BookInput): Book | null {
      const existing = stmtGet.get(id);
      if (!existing) return null;
      const n = mergeUpdate(existing, input);
      return stmtUpdate.get(n.title, n.author, n.year, n.isbn, id) ?? null;
    },
    delete(id: number): boolean {
      return stmtDelete.get(id) !== null;
    },
    close(): void {
      db.close();
    },
  };
}
