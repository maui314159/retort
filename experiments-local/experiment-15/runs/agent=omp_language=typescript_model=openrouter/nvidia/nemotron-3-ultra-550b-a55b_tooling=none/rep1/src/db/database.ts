import Database from 'better-sqlite3';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Book, CreateBookInput, UpdateBookInput, BookFilters } from '../types/book';

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');
const dbPath = resolve(__dirname, '..', '..', 'books.db');

const db = new Database(dbPath);

function initializeDatabase(): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
  `);
}

function mapRow(row: Record<string, unknown>): Book {
  return {
    id: row.id as number,
    title: row.title as string,
    author: row.author as string,
    year: row.year as number | null,
    isbn: row.isbn as string | null,
    createdAt: row.created_at as string,
    updatedAt: row.updated_at as string,
  };
}

export function createBook(input: CreateBookInput): Book {
  const now = new Date().toISOString();
  const stmt = db.prepare(`
    INSERT INTO books (title, author, year, isbn, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  const result = stmt.run(input.title, input.author, input.year ?? null, input.isbn ?? null, now, now);
  return getBookById(result.lastInsertRowid as number)!;
}

export function getAllBooks(filters: BookFilters = {}): Book[] {
  let sql = 'SELECT * FROM books';
  const params: unknown[] = [];

  if (filters.author) {
    sql += ' WHERE author LIKE ?';
    params.push(`%${filters.author}%`);
  }

  sql += ' ORDER BY created_at DESC';

  const stmt = db.prepare(sql);
  const rows = stmt.all(...params) as Record<string, unknown>[];
  return rows.map(mapRow);
}

export function getBookById(id: number): Book | null {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const row = stmt.get(id) as Record<string, unknown> | undefined;
  return row ? mapRow(row) : null;
}

export function updateBook(id: number, input: UpdateBookInput): Book | null {
  const existing = getBookById(id);
  if (!existing) return null;

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

  if (updates.length === 0) return existing;

  updates.push('updated_at = ?');
  params.push(new Date().toISOString());
  params.push(id);

  const stmt = db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`);
  stmt.run(...params);

  return getBookById(id);
}

export function deleteBook(id: number): boolean {
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}

export function closeDatabase(): void {
  db.close();
}

initializeDatabase();