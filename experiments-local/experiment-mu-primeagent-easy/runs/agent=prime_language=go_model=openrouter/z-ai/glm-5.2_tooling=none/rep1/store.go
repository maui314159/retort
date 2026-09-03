package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// Store provides persistence for books using an embedded SQLite database.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures the
// schema is in place. Pass ":memory:" for an ephemeral in-process database,
// useful for tests.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	// Allow only one writer at a time but many readers; SQLite handles this
	// well with WAL, but for an embedded single-process service the default
	// is fine.
	if _, err := db.Exec(`
CREATE TABLE IF NOT EXISTS books (
	id    INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	author TEXT NOT NULL,
	year  INTEGER NOT NULL DEFAULT 0,
	isbn  TEXT NOT NULL DEFAULT ''
);
	`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}

	return &Store{db: db}, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

// CreateBook inserts a new book and returns the stored record with its ID.
func (s *Store) CreateBook(in BookInput) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN,
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// ListBooks returns all books, optionally filtered by author.
func (s *Store) ListBooks(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author == "" {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`, author)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}

// GetBook returns a single book by ID, or false if not found.
func (s *Store) GetBook(id int64) (Book, bool, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return Book{}, false, nil
	}
	if err != nil {
		return Book{}, false, fmt.Errorf("get book: %w", err)
	}
	return b, true, nil
}

// UpdateBook replaces all editable fields of the book with the given ID.
// Returns the updated book and whether a row existed.
func (s *Store) UpdateBook(id int64, in BookInput) (Book, bool, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id,
	)
	if err != nil {
		return Book{}, false, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, false, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return Book{}, false, nil
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, true, nil
}

// DeleteBook removes the book with the given ID and returns whether a row
// was deleted.
func (s *Store) DeleteBook(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}
