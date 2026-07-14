import Database from 'better-sqlite3';
import { Book, NewBook, UpdateBook } from '../models/book';

function assertBookRow(value: unknown): asserts value is Book {
  if (typeof value !== 'object' || value === null) throw new Error('not an object');
  const obj = value as unknown as { [key: string]: unknown };
  if (typeof obj['id'] !== 'number') throw new Error('id must be number');
  if (typeof obj['title'] !== 'string') throw new Error('title must be string');
  if (typeof obj['author'] !== 'string') throw new Error('author must be string');
}

function toBook(row: unknown): Book {
  assertBookRow(row);
  const r = row as unknown as { year: number | null; isbn: string | null };
  return {
    id: (row as Book).id,
    title: (row as Book).title,
    author: (row as Book).author,
    year: r.year !== null ? r.year : undefined,
    isbn: r.isbn !== null ? r.isbn : undefined,
  };
}

const SCHEMA_SQL = `
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
  );
`;

export class BookDatabase {
  private db: Database.Database;

  constructor(dbPath: string = ':memory:') {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.exec(SCHEMA_SQL);
  }

  close(): void {
    this.db.close();
  }

  createBook(book: NewBook): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(book.title, book.author, book.year ?? null, book.isbn ?? null);
    return { id: Number(info.lastInsertRowid), ...book };
  }

  getAllBooks(filterAuthor?: string): Book[] {
    if (filterAuthor) {
      const stmt = this.db.prepare('SELECT * FROM books WHERE author LIKE ? ORDER BY id');
      const rows = stmt.all(`%${filterAuthor}%`);
      return rows.map(toBook);
    }
    const stmt = this.db.prepare('SELECT * FROM books ORDER BY id');
    return stmt.all().map(toBook);
  }

  getBookById(id: number): Book | undefined {
    const stmt = this.db.prepare('SELECT * FROM books WHERE id = ?');
    const row = stmt.get(id);
    return row !== undefined ? toBook(row) : undefined;
  }

  updateBook(id: number, updates: UpdateBook): Book | undefined {
    const existing = this.getBookById(id);
    if (!existing) return undefined;

    const sets: string[] = [];
    const values: (string | number | null)[] = [];

    if (updates.title !== undefined) {
      sets.push('title = ?');
      values.push(updates.title);
    }
    if (updates.author !== undefined) {
      sets.push('author = ?');
      values.push(updates.author);
    }
    if (updates.year !== undefined) {
      sets.push('year = ?');
      values.push(updates.year);
    }
    if (updates.isbn !== undefined) {
      sets.push('isbn = ?');
      values.push(updates.isbn);
    }

    if (sets.length === 0) return existing;

    values.push(id);
    const stmt = this.db.prepare(`UPDATE books SET ${sets.join(', ')} WHERE id = ?`);
    stmt.run(...values);

    return this.getBookById(id);
  }

  deleteBook(id: number): boolean {
    const stmt = this.db.prepare('DELETE FROM books WHERE id = ?');
    const info = stmt.run(id);
    return info.changes > 0;
  }

  healthCheck(): boolean {
    try {
      this.db.prepare('SELECT 1').get();
      return true;
    } catch {
      return false;
    }
  }
}
