import Database from "better-sqlite3";

export interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
`;

export class BookStore {
  private db: Database.Database;

  constructor(dbPath: string = ":memory:") {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.exec(SCHEMA);
  }

  listAll(authorFilter?: string): BookRow[] {
    if (authorFilter && authorFilter.trim().length > 0) {
      const stmt = this.db.prepare(
        "SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE ORDER BY id ASC"
      );
      return stmt.all(`%${authorFilter}%`) as BookRow[];
    }
    const stmt = this.db.prepare("SELECT * FROM books ORDER BY id ASC");
    return stmt.all() as BookRow[];
  }

  getById(id: number): BookRow | undefined {
    const stmt = this.db.prepare("SELECT * FROM books WHERE id = ?");
    return stmt.get(id) as BookRow | undefined;
  }

  create(input: BookInput): BookRow {
    const stmt = this.db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const info = stmt.run(
      input.title,
      input.author,
      input.year,
      input.isbn
    );
    return this.getById(Number(info.lastInsertRowid)) as BookRow;
  }

  update(id: number, input: BookInput): BookRow | undefined {
    if (!this.getById(id)) return undefined;
    const stmt = this.db.prepare(
      `UPDATE books
       SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now')
       WHERE id = ?`
    );
    stmt.run(input.title, input.author, input.year, input.isbn, id);
    return this.getById(id);
  }

  delete(id: number): boolean {
    const stmt = this.db.prepare("DELETE FROM books WHERE id = ?");
    const info = stmt.run(id);
    return info.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
