import Database from 'better-sqlite3';
import path from 'path';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBookInput {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface UpdateBookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export class BookDatabase {
  private db: Database.Database;

  constructor(dbPath?: string) {
    this.db = new Database(dbPath || path.join(process.cwd(), 'books.db'));
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        isbn TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  create(book: CreateBookInput): Book {
    const stmt = this.db.prepare(`
      INSERT INTO books (title, author, year, isbn)
      VALUES (?, ?, ?, ?)
      RETURNING *
    `);
    
    return stmt.get(book.title, book.author, book.year, book.isbn) as Book;
  }

  findAll(author?: string): Book[] {
    if (author) {
      const stmt = this.db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id');
      return stmt.all(author) as Book[];
    }
    const stmt = this.db.prepare('SELECT * FROM books ORDER BY id');
    return stmt.all() as Book[];
  }

  findById(id: number): Book | null {
    const stmt = this.db.prepare('SELECT * FROM books WHERE id = ?');
    const result = stmt.get(id) as Book | undefined;
    return result || null;
  }

  update(id: number, updates: UpdateBookInput): Book | null {
    const existing = this.findById(id);
    if (!existing) return null;

    const fields = [];
    const values = [];
    
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

    if (fields.length === 0) return existing;

    fields.push('updated_at = CURRENT_TIMESTAMP');
    values.push(id);

    const stmt = this.db.prepare(`
      UPDATE books 
      SET ${fields.join(', ')}
      WHERE id = ?
      RETURNING *
    `);

    const result = stmt.get(...values) as Book | undefined;
    return result || null;
  }

  delete(id: number): boolean {
    const stmt = this.db.prepare('DELETE FROM books WHERE id = ?');
    const result = stmt.run(id);
    return result.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}