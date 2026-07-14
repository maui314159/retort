import Database from 'better-sqlite3';

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
  year?: number;
  isbn?: string;
}

export function createDb(filename: string = ':memory:'): Database.Database {
  const db = new Database(filename);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return db;
}

export function insertBook(db: Database.Database, input: BookInput): Book {
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const result = stmt.run(input.title, input.author, input.year ?? null, input.isbn ?? null);
  return { id: result.lastInsertRowid as number, ...input, year: input.year ?? null, isbn: input.isbn ?? null };
}

export function getAllBooks(db: Database.Database, author?: string): Book[] {
  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    return stmt.all(author) as Book[];
  }
  const stmt = db.prepare('SELECT * FROM books');
  return stmt.all() as Book[];
}

export function getBookById(db: Database.Database, id: number): Book | undefined {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  return stmt.get(id) as Book | undefined;
}

export function updateBook(db: Database.Database, id: number, input: Partial<BookInput>): Book | undefined {
  const existing = getBookById(db, id);
  if (!existing) return undefined;

  const title = input.title ?? existing.title;
  const author = input.author ?? existing.author;
  const year = input.year !== undefined ? input.year : existing.year;
  const isbn = input.isbn !== undefined ? input.isbn : existing.isbn;

  const stmt = db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  );
  stmt.run(title, author, year, isbn, id);
  return { id, title, author, year, isbn };
}

export function deleteBook(db: Database.Database, id: number): boolean {
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}
