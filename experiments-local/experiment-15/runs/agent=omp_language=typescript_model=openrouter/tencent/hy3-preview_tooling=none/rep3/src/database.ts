import sqlite3 from 'sqlite3';
import { Book, CreateBookInput, UpdateBookInput } from './types.js';

export class Database {
  private db: sqlite3.Database;
  private initialized: Promise<void>;

  constructor(dbPath: string = ':memory:') {
    this.db = new sqlite3.Database(dbPath);
    this.initialized = this.initializeSchema();
  }

  private initializeSchema(): Promise<void> {
    const { promise, resolve, reject } = Promise.withResolvers<void>();
    
    const schema = `
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `;
    
    this.db.run(schema, (err: Error | null) => {
      if (err) {
        reject(err);
      } else {
        resolve();
      }
    });
    
    return promise;
  }

  private async ensureInitialized(): Promise<void> {
    await this.initialized;
  }

  async createBook(input: CreateBookInput): Promise<Book> {
    await this.ensureInitialized();
    
    const { promise, resolve, reject } = Promise.withResolvers<Book>();
    
    const sql = `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`;
    this.db.run(
      sql,
      [input.title, input.author, input.year ?? null, input.isbn ?? null],
      function (this: sqlite3.RunResult, err: Error | null) {
        if (err) {
          reject(err);
        } else {
          resolve({
            id: this.lastID,
            title: input.title,
            author: input.author,
            year: input.year,
            isbn: input.isbn,
          });
        }
      }
    );
    
    return promise;
  }

  async getAllBooks(authorFilter?: string): Promise<Book[]> {
    await this.ensureInitialized();
    
    const { promise, resolve, reject } = Promise.withResolvers<Book[]>();
    
    let sql = `SELECT id, title, author, year, isbn FROM books`;
    const params: unknown[] = [];
    
    if (authorFilter) {
      sql += ` WHERE author LIKE ?`;
      params.push(`%${authorFilter}%`);
    }
    
    sql += ` ORDER BY id`;
    
    this.db.all(sql, params, (err: Error | null, rows: unknown[]) => {
      if (err) {
        reject(err);
      } else {
        const books = rows as Book[];
        resolve(books);
      }
    });
    
    return promise;
  }

  async getBookById(id: number): Promise<Book | undefined> {
    await this.ensureInitialized();
    
    const { promise, resolve, reject } = Promise.withResolvers<Book | undefined>();
    
    const sql = `SELECT id, title, author, year, isbn FROM books WHERE id = ?`;
    this.db.get(sql, [id], (err: Error | null, row: unknown) => {
      if (err) {
        reject(err);
      } else {
        resolve(row as Book | undefined);
      }
    });
    
    return promise;
  }

  async updateBook(id: number, input: UpdateBookInput): Promise<Book | undefined> {
    await this.ensureInitialized();
    
    const existingBook = await this.getBookById(id);
    if (!existingBook) {
      return undefined;
    }
    
    const updates: string[] = [];
    const params: unknown[] = [];
    
    if (input.title !== undefined) {
      updates.push(`title = ?`);
      params.push(input.title);
    }
    if (input.author !== undefined) {
      updates.push(`author = ?`);
      params.push(input.author);
    }
    if (input.year !== undefined) {
      updates.push(`year = ?`);
      params.push(input.year);
    }
    if (input.isbn !== undefined) {
      updates.push(`isbn = ?`);
      params.push(input.isbn);
    }
    
    updates.push(`updated_at = CURRENT_TIMESTAMP`);
    
    const sql = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;
    params.push(id);
    
    const { promise, resolve, reject } = Promise.withResolvers<Book>();
    
    this.db.run(sql, params, (err: Error | null) => {
      if (err) {
        reject(err);
      } else {
        const updatedBook: Book = {
          id,
          title: input.title ?? existingBook.title,
          author: input.author ?? existingBook.author,
          year: input.year ?? existingBook.year,
          isbn: input.isbn ?? existingBook.isbn,
        };
        resolve(updatedBook);
      }
    });
    
    return promise;
  }

  async deleteBook(id: number): Promise<boolean> {
    await this.ensureInitialized();
    
    const { promise, resolve, reject } = Promise.withResolvers<boolean>();
    
    const sql = `DELETE FROM books WHERE id = ?`;
    this.db.run(sql, [id], function (this: sqlite3.RunResult, err: Error | null) {
      if (err) {
        reject(err);
      } else {
        resolve(this.changes > 0);
      }
    });
    
    return promise;
  }

  close(): void {
    this.db.close();
  }
}
