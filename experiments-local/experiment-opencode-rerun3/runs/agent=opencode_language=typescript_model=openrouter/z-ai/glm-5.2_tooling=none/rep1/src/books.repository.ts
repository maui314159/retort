import type { DB, BookRow } from "./db.js";

export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export class BooksRepository {
  constructor(private db: DB) {}

  create(input: BookInput): BookRow {
    const stmt = this.db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const info = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    const id = info.lastInsertRowid as number;
    const row = this.getById(id);
    if (!row) throw new Error("insert failed");
    return row;
  }

  list(filter?: { author?: string }): BookRow[] {
    if (filter?.author) {
      return this.db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(filter.author) as BookRow[];
    }
    return this.db.prepare("SELECT * FROM books ORDER BY id").all() as BookRow[];
  }

  getById(id: number): BookRow | undefined {
    return this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      | BookRow
      | undefined;
  }

  update(id: number, input: Partial<BookInput>): BookRow | undefined {
    const existing = this.getById(id);
    if (!existing) return undefined;
    const next = {
      title: input.title ?? existing.title,
      author: input.author ?? existing.author,
      year: input.year ?? existing.year,
      isbn: input.isbn ?? existing.isbn,
    };
    this.db
      .prepare(
        "UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=datetime('now') WHERE id=?"
      )
      .run(next.title, next.author, next.year, next.isbn, id);
    return this.getById(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return info.changes > 0;
  }
}
