package main

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite"
)

var (
	// ErrNotFound is returned when no row matches the given id.
	ErrNotFound = errors.New("book not found")
)

// Store is the persistence layer for books, backed by SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures the
// schema is present. Pass ":memory:" for an ephemeral database.
func NewStore(path string) (*Store, error) {
	// busy_timeout lets connections wait briefly on locks instead of failing
	// immediately; foreign_keys is good hygiene.
	dsn := fmt.Sprintf("%s?_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)", path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite serializes writes through a single global lock; one connection
	// in the pool is sufficient and avoids "database is locked" contention.
	db.SetMaxOpenConns(1)

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	const schema = `
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER NOT NULL DEFAULT 0,
    isbn       TEXT    NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);`
	_, err := s.db.Exec(schema)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}

// Close releases the underlying database connection.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a book and returns the stored row with its generated id.
func (s *Store) Create(b *Book) (*Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	return s.Get(id)
}

// Get returns a single book by id.
func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`,
		id,
	)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return b, nil
}

// List returns all books, optionally filtered by author. An empty author
// filter returns every row.
func (s *Store) List(author string) ([]*Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author = trim(author); author != "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ? ORDER BY id`,
			author,
		)
	} else {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id`,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Update replaces the mutable fields of the book identified by id.
func (s *Store) Update(id int64, b *Book) (*Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, err
	}
	if n == 0 {
		return nil, ErrNotFound
	}
	return s.Get(id)
}

// Delete removes a book by id. It is idempotent: deleting a missing id is not
// an error (returns false, nil).
func (s *Store) Delete(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// scanner abstracts *sql.Row and *sql.Rows for shared scan logic.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(s scanner) (*Book, error) {
	b := &Book{}
	err := s.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return b, nil
}

func trim(s string) string { return strings.TrimSpace(s) }
