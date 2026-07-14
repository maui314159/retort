import Database from 'better-sqlite3';
import { Book, CreateBookInput, UpdateBookInput } from './Book';

export class BookDatabase {
  private db: Database.Database | null = null;

  initialize(dbPath: string = ':memory:'): void {
    this.db = new Database(dbPath);
    this.createTables();
  }

  private createTables(): void {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `;

    this.db!.exec(createTableSQL);
  }

  createBook(input: CreateBookInput): Book {
    const now = new Date().toISOString();
    const sql = `
      INSERT INTO books (title, author, year, isbn, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `;

    const stmt = this.db!.prepare(sql);
    const result = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null,
      now,
      now
    );

    return {
      id: Number(result.lastInsertRowid),
      title: input.title,
      author: input.author,
      year: input.year,
      isbn: input.isbn,
      created_at: now,
      updated_at: now,
    };
  }

  getAllBooks(authorFilter?: string): Book[] {
    let sql = 'SELECT * FROM books';
    let params: unknown[] = [];

    if (authorFilter) {
      sql += ' WHERE author LIKE ?';
      params.push(`%${authorFilter}%`);
    }

    sql += ' ORDER BY id ASC';

    const stmt = this.db!.prepare(sql);
    const rows = stmt.all(...params) as Record<string, unknown>[];

    return rows.map((row) => this.mapRowToBook(row));
  }

  getBookById(id: number): Book | null {
    const sql = 'SELECT * FROM books WHERE id = ?';
    const stmt = this.db!.prepare(sql);
    const row = stmt.get(id) as Record<string, unknown> | undefined;

    if (!row) {
      return null;
    }

    return this.mapRowToBook(row);
  }

  updateBook(id: number, input: UpdateBookInput): Book | null {
    const existing = this.getBookById(id);
    if (!existing) {
      return null;
    }

    const now = new Date().toISOString();
    const updates: string[] = [];
    const params: unknown[] = [];

    if (input.title !== undefined) {
      updates.push('title = ?');
      params.push(input.title);
    }

    if (input.author !== undefined) {
      updates.push('author = ?');
      params.push(input.author);
    }

    if (input.year !== undefined) {
      updates.push('year = ?');
      params.push(input.year);
    }

    if (input.isbn !== undefined) {
      updates.push('isbn = ?');
      params.push(input.isbn);
    }

    updates.push('updated_at = ?');
    params.push(now);
    params.push(id);

    const sql = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;

    const stmt = this.db!.prepare(sql);
    stmt.run(...params);

    return {
      ...existing,
      ...input,
      updated_at: now,
    };
  }

  deleteBook(id: number): boolean {
    const sql = 'DELETE FROM books WHERE id = ?';
    const stmt = this.db!.prepare(sql);
    const result = stmt.run(id);

    return result.changes > 0;
  }

  clear(): void {
    this.db!.exec('DELETE FROM books');
  }

  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  private mapRowToBook(row: Record<string, unknown>): Book {
    return {
      id: Number(row.id),
      title: String(row.title),
      author: String(row.author),
      year: row.year !== null ? Number(row.year) : undefined,
      isbn: row.isbn !== null ? String(row.isbn) : undefined,
      created_at: String(row.created_at),
      updated_at: String(row.updated_at),
    };
  }
}
