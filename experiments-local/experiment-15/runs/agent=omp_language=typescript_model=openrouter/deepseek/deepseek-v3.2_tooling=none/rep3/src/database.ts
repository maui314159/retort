import Database from 'better-sqlite3';
import { Book, CreateBookRequest, UpdateBookRequest } from './types';

export class BookDatabase {
  private db: Database.Database;

  constructor(filePath: string = ':memory:') {
    this.db = new Database(filePath);
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        isbn TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  createBook(book: CreateBookRequest): Book {
    const stmt = this.db.prepare(`
      INSERT INTO books (title, author, year, isbn)
      VALUES (?, ?, ?, ?)
    `);
    const result = stmt.run(book.title, book.author, book.year, book.isbn);
    
    const id = result.lastInsertRowid;
    if (typeof id !== 'number') {
      throw new Error('Failed to insert book');
    }

    return {
      id,
      title: book.title,
      author: book.author,
      year: book.year,
      isbn: book.isbn
    };
  }

  getAllBooks(author?: string): Book[] {
    let query = 'SELECT * FROM books';
    const params: unknown[] = [];
    
    if (author) {
      query += ' WHERE author = ?';
      params.push(author);
    }
    
    query += ' ORDER BY created_at DESC';
    
    const stmt = this.db.prepare(query);
    return stmt.all(...params) as Book[];
  }

  getBookById(id: number): Book | null {
    const stmt = this.db.prepare('SELECT * FROM books WHERE id = ?');
    const book = stmt.get(id) as Book | undefined;
    return book || null;
  }

  updateBook(id: number, updates: UpdateBookRequest): Book | null {
    const existing = this.getBookById(id);
    if (!existing) {
      return null;
    }

    const fields: string[] = [];
    const values: unknown[] = [];

    if (updates.title !== undefined) {
      fields.push('title = ?');
      values.push(updates.title);
    }
    if (updates.author !== undefined) {
      fields.push('author = ?');
      values.push(updates.author);
    }
    if (updates.year !== undefined) {
      fields.push('year = ?');
      values.push(updates.year);
    }
    if (updates.isbn !== undefined) {
      fields.push('isbn = ?');
      values.push(updates.isbn);
    }

    if (fields.length === 0) {
      return existing;
    }

    values.push(id);
    const stmt = this.db.prepare(`
      UPDATE books
      SET ${fields.join(', ')}
      WHERE id = ?
    `);
    stmt.run(...values);

    const updated = this.getBookById(id);
    return updated;
  }

  deleteBook(id: number): boolean {
    const stmt = this.db.prepare('DELETE FROM books WHERE id = ?');
    const result = stmt.run(id);
    return result.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}