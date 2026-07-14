import Database from 'better-sqlite3';
import type { Database as DB } from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface NewBook {
  title: string;
  author: string;
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

export class BookStore {
  private db: DB;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.exec(CREATE_TABLE_SQL);
  }

  insert(book: NewBook): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(
      book.title,
      book.author,
      book.year ?? null,
      book.isbn ?? null
    );
    return this.getById(info.lastInsertRowid as number) as Book;
  }

  list(author?: string): Book[] {
    if (author) {
      return this.db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id ASC')
        .all(author) as Book[];
    }
    return this.db.prepare('SELECT * FROM books ORDER BY id ASC').all() as Book[];
  }

  getById(id: number): Book | undefined {
    return this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as
      | Book
      | undefined;
  }

  update(id: number, book: NewBook): Book | undefined {
    const stmt = this.db.prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    );
    stmt.run(
      book.title,
      book.author,
      book.year ?? null,
      book.isbn ?? null,
      id
    );
    return this.getById(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return info.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
