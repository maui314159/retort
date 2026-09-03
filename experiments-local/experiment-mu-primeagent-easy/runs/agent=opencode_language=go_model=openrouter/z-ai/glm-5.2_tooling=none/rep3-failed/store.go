package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// Store wraps the SQLite database for book persistence.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) a SQLite database at path and initializes schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// Enable foreign keys and reasonable concurrency for tests.
	if _, err := db.Exec("PRAGMA foreign_keys = ON;"); err != nil {
		db.Close()
		return nil, err
	}
	s := &Store{db: db}
	if err := s.init(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) init() error {
	_, err := s.db.Exec(`
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER NOT NULL DEFAULT 0,
    isbn   TEXT    NOT NULL DEFAULT ''
);`)
	return err
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a book and returns the stored book with its new ID.
func (s *Store) Create(b *Book) (*Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?);`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return nil, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, err
	}
	b.ID = id
	return b, nil
}

// List returns all books, optionally filtered by author.
func (s *Store) List(author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []interface{}
	if author != "" {
		q += ` WHERE author = ?`
		args = append(args, author)
	}
	q += ` ORDER BY id ASC;`
	rows, err := s.db.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Get fetches a single book by ID. Returns nil, nil when not found.
func (s *Store) Get(id int64) (*Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?;`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &b, nil
}

// Update fully replaces a book row. Returns false if no row matched id.
func (s *Store) Update(id int64, b *Book) (bool, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?;`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return false, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// Delete removes a book. Returns false if no row matched id.
func (s *Store) Delete(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?;`, id)
	if err != nil {
		return false, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}
