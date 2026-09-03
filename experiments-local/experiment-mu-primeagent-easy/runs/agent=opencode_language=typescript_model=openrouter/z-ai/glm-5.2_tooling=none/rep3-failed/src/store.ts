import Database from "better-sqlite3";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: unknown;
  author: unknown;
  year?: unknown;
  isbn?: unknown;
}

export class BookStore {
  private db: Database.Database;

  constructor(dbPath: string = ":memory:") {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.init();
  }

  private init(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year  INTEGER,
        isbn  TEXT
      )
    `);
  }

  all(author?: string): Book[] {
    if (author) {
      return this.db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author) as Book[];
    }
    return this.db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      | Book
      | undefined;
  }

  create(input: BookInput): Book {
    const { title, author, year, isbn } = coerceBook(input);
    const info = this.db
      .prepare(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
      )
      .run(title, author, year, isbn);
    return this.get(Number(info.lastInsertRowid)) as Book;
  }

  update(id: number, input: BookInput): Book | undefined {
    const existing = this.get(id);
    if (!existing) return undefined;
    const { title, author, year, isbn } = coerceBook(input);
    this.db
      .prepare(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
      )
      .run(title, author, year, isbn, id);
    return this.get(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return info.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}

export function coerceBook(input: BookInput): {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
} {
  const title = typeof input.title === "string" ? input.title.trim() : "";
  const author = typeof input.author === "string" ? input.author.trim() : "";
  if (!title) throw new ValidationError("title is required");
  if (!author) throw new ValidationError("author is required");

  let year: number | null = null;
  if (input.year !== undefined && input.year !== null) {
    const n = Number(input.year);
    if (Number.isNaN(n) || !Number.isInteger(n))
      throw new ValidationError("year must be an integer");
    year = n;
  }

  let isbn: string | null = null;
  if (input.isbn !== undefined && input.isbn !== null) {
    isbn = String(input.isbn).trim() || null;
  }

  return { title, author, year, isbn };
}

export class ValidationError extends Error {
  status = 400;
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}
