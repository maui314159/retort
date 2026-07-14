import type { Book, BookCreate, BookUpdate } from "./types.js";
import type { Db } from "./db.js";

export class BookRepository {
  constructor(private readonly db: Db) {}

  create(input: BookCreate): Book {
    const stmt = this.db.prepare(
      `INSERT INTO books (title, author, year, isbn)
       VALUES (@title, @author, @year, @isbn)`,
    );
    const result = stmt.run({
      title: input.title,
      author: input.author,
      year: input.year ?? null,
      isbn: input.isbn ?? null,
    });
    const id = Number(result.lastInsertRowid);
    const book = this.findById(id);
    if (!book) {
      throw new Error("Inserted book not found");
    }
    return book;
  }

  findAll(filter?: { author?: string }): Book[] {
    if (filter?.author) {
      const stmt = this.db.prepare(
        `SELECT * FROM books WHERE author = @author ORDER BY id ASC`,
      );
      return stmt.all({ author: filter.author }) as Book[];
    }
    const stmt = this.db.prepare(`SELECT * FROM books ORDER BY id ASC`);
    return stmt.all() as Book[];
  }

  findById(id: number): Book | null {
    const stmt = this.db.prepare(`SELECT * FROM books WHERE id = @id`);
    const row = stmt.get({ id }) as Book | undefined;
    return row ?? null;
  }

  update(id: number, patch: BookUpdate): Book | null {
    const current = this.findById(id);
    if (!current) return null;

    const next = {
      title: patch.title ?? current.title,
      author: patch.author ?? current.author,
      year: patch.year === undefined ? current.year : patch.year,
      isbn: patch.isbn === undefined ? current.isbn : patch.isbn,
    };

    const stmt = this.db.prepare(
      `UPDATE books
         SET title = @title,
             author = @author,
             year = @year,
             isbn = @isbn,
             updated_at = datetime('now')
       WHERE id = @id`,
    );
    stmt.run({ id, ...next });
    return this.findById(id);
  }

  delete(id: number): boolean {
    const stmt = this.db.prepare(`DELETE FROM books WHERE id = @id`);
    const result = stmt.run({ id });
    return result.changes > 0;
  }
}
