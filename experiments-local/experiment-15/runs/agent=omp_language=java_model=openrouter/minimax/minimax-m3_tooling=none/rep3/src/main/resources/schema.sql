CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year  INTEGER,
    isbn  TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
