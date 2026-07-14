import Database from "better-sqlite3";
import type { Database as BetterSqlite3Database } from "better-sqlite3";
import type { BookInput } from "./validation.js";

export type { BookInput } from "./validation.js";

export interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  createdAt: string;
  updatedAt: string;
}

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`;

function rowToBook(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export interface BookRepository {
  list(author?: string): Book[];
  get(id: number): Book | null;
  create(input: BookInput): Book;
  update(id: number, input: BookInput): Book | null;
  remove(id: number): boolean;
  close(): void;
}

export function createRepository(db: BetterSqlite3Database): BookRepository {
  db.exec(SCHEMA);

  const stmtListAll = db.prepare("SELECT * FROM books ORDER BY id");
  const stmtListByAuthor = db.prepare<[string]>(
    "SELECT * FROM books WHERE author = ? ORDER BY id"
  );
  const stmtGet = db.prepare<[number]>("SELECT * FROM books WHERE id = ?");
  const stmtInsert = db.prepare<BookInput>(
    "INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn) RETURNING *"
  );
  const stmtUpdate = db.prepare<BookInput & { id: number }>(
    "UPDATE books SET title = @title, author = @author, year = @year, isbn = @isbn, updated_at = datetime('now') WHERE id = @id RETURNING *"
  );
  const stmtDelete = db.prepare<[number]>("DELETE FROM books WHERE id = ?");
  const stmtTouch = db.prepare<[number]>("SELECT 1 FROM books WHERE id = ?");

  return {
    list(author) {
      const rows = (
        author ? (stmtListByAuthor.all(author) as BookRow[]) : (stmtListAll.all() as BookRow[])
      );
      return rows.map(rowToBook);
    },
    get(id) {
      const row = stmtGet.get(id) as BookRow | undefined;
      return row ? rowToBook(row) : null;
    },
    create(input) {
      const row = stmtInsert.get(input) as BookRow;
      return rowToBook(row);
    },
    update(id, input) {
      const existing = stmtTouch.get(id);
      if (!existing) return null;
      const row = stmtUpdate.get({ id, ...input }) as BookRow;
      return rowToBook(row);
    },
    remove(id) {
      const info = stmtDelete.run(id);
      return info.changes > 0;
    },
    close() {
      db.close();
    },
  };
}

export function openDatabase(filename: string = ":memory:"): BetterSqlite3Database {
  return new Database(filename);
}
