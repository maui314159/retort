import Database from 'better-sqlite3';
import type { Database as DB } from 'better-sqlite3';

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
  year?: number | null;
  isbn?: string | null;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}

const CREATE_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  );
`;

const CREATE_INDEX_SQL = `
  CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`;

export class BookStore {
  private db: DB;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.exec(CREATE_TABLE_SQL);
    this.db.exec(CREATE_INDEX_SQL);
  }

  create(input: BookInput): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.getById(Number(info.lastInsertRowid)) as Book;
  }

  list(author?: string): Book[] {
    if (author) {
      return this.db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    }
    return this.db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
  }

  getById(id: number): Book | undefined {
    return this.db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(id) as Book | undefined;
  }

  update(id: number, input: BookUpdate): Book | undefined {
    const existing = this.getById(id);
    if (!existing) return undefined;

    const next: Book = {
      ...existing,
      ...input,
      id,
      title: input.title !== undefined ? input.title : existing.title,
      author: input.author !== undefined ? input.author : existing.author,
      year: input.year !== undefined ? (input.year ?? null) : existing.year,
      isbn: input.isbn !== undefined ? (input.isbn ?? null) : existing.isbn,
    };

    this.db
      .prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(next.title, next.author, next.year, next.isbn, id);

    return next;
  }

  delete(id: number): boolean {
    const info = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return info.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
