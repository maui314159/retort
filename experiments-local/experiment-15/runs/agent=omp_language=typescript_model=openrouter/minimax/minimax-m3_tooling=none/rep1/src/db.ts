import Database from 'better-sqlite3';

export type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

export type BookInput = {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
};

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT    NOT NULL,
  author TEXT   NOT NULL,
  year  INTEGER,
  isbn  TEXT
);
`;

export type BookStore = {
  create: (input: BookInput) => Book;
  list: (filter?: { author?: string }) => Book[];
  get: (id: number) => Book | undefined;
  update: (id: number, input: BookInput) => Book | undefined;
  remove: (id: number) => boolean;
  close: () => void;
};

export function openBookStore(path: string = ':memory:'): BookStore {
  const db = new Database(path);
  db.exec(SCHEMA);

  const insertStmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const listAllStmt = db.prepare(
    'SELECT id, title, author, year, isbn FROM books ORDER BY id ASC'
  );
  // Substring match (case-insensitive) on author. Escape user input so a literal
  // `%` or `_` in the query string cannot act as a wildcard.
  const listByAuthorStmt = db.prepare(
    "SELECT id, title, author, year, isbn FROM books WHERE LOWER(author) LIKE LOWER(?) ESCAPE '\\' ORDER BY id ASC"
  );
  const getStmt = db.prepare(
    'SELECT id, title, author, year, isbn FROM books WHERE id = ?'
  );
  const updateStmt = db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  );
  const deleteStmt = db.prepare('DELETE FROM books WHERE id = ?');

  function create(input: BookInput): Book {
    const result = insertStmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    const id = Number(result.lastInsertRowid);
    return {
      id,
      title: input.title,
      author: input.author,
      year: input.year ?? null,
      isbn: input.isbn ?? null,
    };
  }

  function list(filter?: { author?: string }): Book[] {
    if (filter?.author) {
      const needle = `%${escapeLike(filter.author)}%`;
      return listByAuthorStmt.all(needle) as Book[];
    }
    return listAllStmt.all() as Book[];
  }

  function get(id: number): Book | undefined {
    return getStmt.get(id) as Book | undefined;
  }

  function update(id: number, input: BookInput): Book | undefined {
    const result = updateStmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null,
      id
    );
    if (result.changes === 0) return undefined;
    return get(id);
  }

  function remove(id: number): boolean {
    const result = deleteStmt.run(id);
    return result.changes > 0;
  }

  function close(): void {
    db.close();
  }

  return { create, list, get, update, remove, close };
}

// Escape LIKE wildcards in untrusted user input so `?author=10%off` matches
// the literal substring "10%off" instead of acting as a pattern.
function escapeLike(input: string): string {
  return input.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
}
