import Database from 'better-sqlite3';
import { Book, CreateBookInput, UpdateBookInput } from './types';

let db: Database.Database | null = null;

export function initDatabase(path: string = process.env.DATABASE_PATH || 'books.sqlite'): Database.Database {
  if (db) return db;

  db = new Database(path);
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
  `);

  return db;
}

export function getDatabase(): Database.Database {
  if (!db) {
    throw new Error('Database not initialized. Call initDatabase() first.');
  }
  return db;
}

export function closeDatabase(): void {
  if (db) {
    db.close();
    db = null;
  }
}

export function resetDatabaseState(): void {
  const database = getDatabase();
  database.exec('DELETE FROM books');
  database.exec("DELETE FROM sqlite_sequence WHERE name = 'books'");
}

export function createBook(input: CreateBookInput): Book {
  const database = getDatabase();
  const stmt = database.prepare(`
    INSERT INTO books (title, author, year, isbn, updated_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    RETURNING *
  `);

  return stmt.get(
    input.title,
    input.author,
    input.year ?? null,
    input.isbn ?? null
  ) as Book;
}

export function listBooks(authorFilter?: string): Book[] {
  const database = getDatabase();

  if (authorFilter) {
    const stmt = database.prepare(`
      SELECT * FROM books WHERE author LIKE ? ORDER BY id
    `);
    return stmt.all(`%${authorFilter}%`) as Book[];
  }

  const stmt = database.prepare('SELECT * FROM books ORDER BY id');
  return stmt.all() as Book[];
}

export function getBookById(id: number): Book | undefined {
  const database = getDatabase();
  const stmt = database.prepare('SELECT * FROM books WHERE id = ?');
  return stmt.get(id) as Book | undefined;
}

export function updateBook(id: number, input: UpdateBookInput): Book | undefined {
  const database = getDatabase();
  const existing = getBookById(id);
  if (!existing) return undefined;

  const title = input.title ?? existing.title;
  const author = input.author ?? existing.author;
  const year = input.year !== undefined ? input.year : existing.year;
  const isbn = input.isbn !== undefined ? input.isbn : existing.isbn;

  const stmt = database.prepare(`
    UPDATE books
    SET title = ?, author = ?, year = ?, isbn = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    RETURNING *
  `);

  return stmt.get(title, author, year, isbn, id) as Book;
}

export function deleteBook(id: number): boolean {
  const database = getDatabase();
  const stmt = database.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}
