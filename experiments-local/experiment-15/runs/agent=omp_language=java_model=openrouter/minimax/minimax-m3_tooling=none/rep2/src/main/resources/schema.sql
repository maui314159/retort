CREATE TABLE IF NOT EXISTS book (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    isbn  TEXT
);

CREATE INDEX IF NOT EXISTS idx_book_author ON book(author);
