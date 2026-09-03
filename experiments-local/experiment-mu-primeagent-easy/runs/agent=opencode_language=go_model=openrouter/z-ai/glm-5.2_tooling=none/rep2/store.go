package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// Store wraps the database connection for book operations.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures the
// schema exists.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	return &Store{db: db}, nil
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id    INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	author TEXT NOT NULL,
	year  INTEGER NOT NULL DEFAULT 0,
	isbn  TEXT NOT NULL DEFAULT ''
);
`

// Close closes the underlying database connection.
func (s *Store) Close() error { return s.db.Close() }

// CreateBook inserts a book and returns it with the assigned ID.
func (s *Store) CreateBook(b *Book) (*Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return nil, fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

// ListBooks returns all books, optionally filtered by author.
func (s *Store) ListBooks(author string) ([]Book, error) {
	q := "SELECT id, title, author, year, isbn FROM books"
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.Query(q+" WHERE author = ? ORDER BY id", author)
	} else {
		rows, err = s.db.Query(q + " ORDER BY id")
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// GetBook returns a single book by ID.
func (s *Store) GetBook(id int64) (*Book, error) {
	var b Book
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get: %w", err)
	}
	return &b, nil
}

// UpdateBook updates an existing book by ID. Returns nil if not found.
func (s *Store) UpdateBook(id int64, b *Book) (*Book, error) {
	res, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, nil
	}
	b.ID = id
	return b, nil
}

// DeleteBook removes a book by ID. Returns true if a row was deleted.
func (s *Store) DeleteBook(id int64) (bool, error) {
	res, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return false, fmt.Errorf("delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}
