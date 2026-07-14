package main

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

// Store provides persistence for books using SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and initializes schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite performs better with a single connection for writes.
	db.SetMaxOpenConns(1)
	s := &Store{db: db}
	if err := s.init(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) init() error {
	const ddl = `
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER NOT NULL DEFAULT 0,
    isbn       TEXT    NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);`
	_, err := s.db.Exec(ddl)
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// ErrNotFound is returned when a book is not present.
var ErrNotFound = errors.New("book not found")

// Create inserts a new book and returns the stored record.
func (s *Store) Create(b Book) (Book, error) {
	now := time.Now().UTC()
	b.CreatedAt = now
	b.UpdatedAt = now
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

// List returns all books, optionally filtered by author (case-insensitive substring).
func (s *Store) List(authorFilter string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books`
	var (
		rows *sql.Rows
		err  error
	)
	if authorFilter != "" {
		q += ` WHERE author LIKE ?`
		rows, err = s.db.Query(q, "%"+authorFilter+"%")
	} else {
		rows, err = s.db.Query(q)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// Get returns a single book by ID.
func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// Update replaces mutable fields of the book identified by id.
func (s *Store) Update(id int64, b Book) (Book, error) {
	b.UpdatedAt = time.Now().UTC()
	res, err := s.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, b.UpdatedAt, id,
	)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	// Re-read to return canonical created_at.
	existing, err := s.Get(id)
	if err != nil {
		return Book{}, err
	}
	b.CreatedAt = existing.CreatedAt
	return b, nil
}

// Delete removes a book by ID.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
