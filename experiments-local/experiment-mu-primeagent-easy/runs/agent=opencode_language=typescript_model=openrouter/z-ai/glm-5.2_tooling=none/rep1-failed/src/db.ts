import Database from "better-sqlite3";
import type { Database as DBInstance } from "better-sqlite3";
import type { Book, BookInput } from "./types.js";

export interface BookDb {
  listBooks(author?: string): Book[];
  getBook(id: number): Book | undefined;
  createBook(input: BookInput): Book;
  updateBook(id: number, input: BookInput): Book | undefined;
  deleteBook(id: number): boolean;
  close(): void;
}

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function normalizeRow(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
  };
}

export function createBookDb(dbPath: string): BookDb {
  const db: DBInstance = new Database(dbPath);
  db.pragma("journal_mode = WAL");

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);

  const listAll = db.prepare<[], BookRow>("SELECT * FROM books ORDER BY id ASC");
  const listByAuthor = db.prepare<{ author: string }, BookRow>(
    "SELECT * FROM books WHERE author = @author ORDER BY id ASC",
  );
  const getById = db.prepare<{ id: number }, BookRow>("SELECT * FROM books WHERE id = @id");
  const insert = db.prepare<
    { title: string; author: string; year: number | null; isbn: string | null },
    BookRow
  >(
    "INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn) RETURNING *",
  );
  const update = db.prepare<
    { id: number; title: string; author: string; year: number | null; isbn: string | null },
    BookRow
  >(
    "UPDATE books SET title = @title, author = @author, year = @year, isbn = @isbn WHERE id = @id RETURNING *",
  );
  const remove = db.prepare<{ id: number }>("DELETE FROM books WHERE id = @id");

  return {
    listBooks(author?: string): Book[] {
      const rows = author ? listByAuthor.all({ author }) : listAll.all();
      return rows.map(normalizeRow);
    },
    getBook(id: number): Book | undefined {
      const row = getById.get({ id });
      return row ? normalizeRow(row) : undefined;
    },
    createBook(input: BookInput): Book {
      const row = insert.get({
        title: input.title,
        author: input.author,
        year: input.year ?? null,
        isbn: input.isbn ?? null,
      });
      if (!row) {
        throw new Error("Failed to create book: no row returned from INSERT.");
      }
      return normalizeRow(row);
    },
    updateBook(id: number, input: BookInput): Book | undefined {
      const row = update.get({
        id,
        title: input.title,
        author: input.author,
        year: input.year ?? null,
        isbn: input.isbn ?? null,
      });
      return row ? normalizeRow(row) : undefined;
    },
    deleteBook(id: number): boolean {
      const result = remove.run({ id });
      return result.changes > 0;
    },
    close(): void {
      db.close();
    },
  };
}
