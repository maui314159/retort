import { DatabaseSync } from "node:sqlite";
import { Book, ValidatedBookInput } from "./types";

// node:sqlite is stable enough for this service but Node still flags it as
// "experimental". Suppress only that specific warning so server and test
// output stays clean, without hiding any other warnings.
{
  const originalEmit = process.emit;
  process.emit = function (name: string | symbol, ...args: any[]): boolean {
    if (
      name === "warning" &&
      args[0] instanceof Error &&
      (args[0] as Error).name === "ExperimentalWarning" &&
      String((args[0] as Error).message).includes("SQLite")
    ) {
      return false;
    }
    return originalEmit.call(process, name, ...args);
  };
}

/**
 * Thin data-access layer over a SQLite database (Node's built-in `node:sqlite`).
 *
 * Pass `":memory:"` as the path to get an ephemeral in-memory database,
 * which is convenient for testing. WAL journaling is enabled for file-backed
 * databases (it is a no-op for in-memory databases).
 */
export class BookStore {
  private db: DatabaseSync;

  constructor(path: string = ":memory:") {
    this.db = new DatabaseSync(path);
    try {
      this.db.exec("PRAGMA journal_mode = WAL");
    } catch {
      // WAL is not applicable to some backends (e.g. :memory:); ignore.
    }
    this.init();
  }

  /** Create the schema. Idempotent so it is safe to call repeatedly. */
  private init(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  /** Return all books, optionally filtered by author (case-insensitive substring). */
  list(author?: string): Book[] {
    if (author === undefined || author === null || author.trim() === "") {
      return this.db.prepare("SELECT * FROM books ORDER BY id ASC").all() as unknown as Book[];
    }
    return this.db
      .prepare("SELECT * FROM books WHERE author LIKE ? ORDER BY id ASC")
      .all(`%${author}%`) as unknown as Book[];
  }

  /** Return a single book by id, or null when not found. */
  get(id: number): Book | null {
    const row = this.db.prepare("SELECT * FROM books WHERE id = ?").get(id);
    return (row ?? null) as unknown as Book | null;
  }

  /** Insert a new book and return the freshly created record. */
  create(input: ValidatedBookInput): Book {
    const now = new Date().toISOString();
    const info = this.db
      .prepare(
        "INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
      )
      .run(input.title, input.author, input.year, input.isbn, now, now);
    // lastInsertRowid is `number | bigint`; Number() normalises both.
    const created = this.get(Number(info.lastInsertRowid));
    return created as Book;
  }

  /** Replace a book's fields and return the updated record, or null if missing. */
  update(id: number, input: ValidatedBookInput): Book | null {
    const existing = this.get(id);
    if (!existing) return null;
    const now = new Date().toISOString();
    this.db
      .prepare(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?"
      )
      .run(input.title, input.author, input.year, input.isbn, now, id);
    return this.get(id);
  }

  /** Delete a book by id. Returns true if a row was deleted, false otherwise. */
  delete(id: number): boolean {
    const info = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return info.changes > 0;
  }

  /** Close the underlying database connection. */
  close(): void {
    this.db.close();
  }
}
