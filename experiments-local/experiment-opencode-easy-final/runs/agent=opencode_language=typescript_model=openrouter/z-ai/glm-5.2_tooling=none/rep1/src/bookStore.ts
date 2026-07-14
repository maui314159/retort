import Database from "better-sqlite3";
import type { Database as DatabaseConnection } from "better-sqlite3";
import type { Book, CreateBookInput, UpdateBookInput } from "./types";

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  );
`;

export class BookStore {
  private db: DatabaseConnection;

  constructor(dbPath: string = ":memory:") {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.exec(SCHEMA);
  }

  create(input: CreateBookInput): Book {
    const stmt = this.db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const result = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.getById(Number(result.lastInsertRowid))!;
  }

  list(authorFilter?: string): Book[] {
    if (authorFilter) {
      const stmt = this.db.prepare(
        "SELECT * FROM books WHERE author = ? ORDER BY id"
      );
      return stmt.all(authorFilter) as Book[];
    }
    const stmt = this.db.prepare("SELECT * FROM books ORDER BY id");
    return stmt.all() as Book[];
  }

  getById(id: number): Book | undefined {
    const stmt = this.db.prepare("SELECT * FROM books WHERE id = ?");
    return stmt.get(id) as Book | undefined;
  }

  update(id: number, input: UpdateBookInput): Book | undefined {
    const existing = this.getById(id);
    if (!existing) return undefined;

    const next: Book = {
      ...existing,
      title: input.title ?? existing.title,
      author: input.author ?? existing.author,
      year: input.year ?? existing.year,
      isbn: input.isbn ?? existing.isbn,
    };

    const stmt = this.db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    );
    stmt.run(next.title, next.author, next.year, next.isbn, id);
    return this.getById(id);
  }

  delete(id: number): boolean {
    const stmt = this.db.prepare("DELETE FROM books WHERE id = ?");
    const result = stmt.run(id);
    return result.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
