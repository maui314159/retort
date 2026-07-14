import { DatabaseSync } from "node:sqlite";
import type { Book, BookInput } from "./types";

export class BookStore {
  private db: DatabaseSync;

  constructor(location = ":memory:") {
    this.db = new DatabaseSync(location);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }

  create(input: BookInput): Book {
    const stmt = this.db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const info = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.get(Number(info.lastInsertRowid))!;
  }

  list(author?: string): Book[] {
    if (author !== undefined) {
      return this.db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author) as unknown as Book[];
    }
    return this.db
      .prepare("SELECT * FROM books ORDER BY id")
      .all() as unknown as Book[];
  }

  get(id: number): Book | undefined {
    const row = this.db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(id);
    return (row as unknown as Book) ?? undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const existing = this.get(id);
    if (!existing) return undefined;
    this.db
      .prepare(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
      )
      .run(
        input.title,
        input.author,
        input.year ?? null,
        input.isbn ?? null,
        id
      );
    return this.get(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return info.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
