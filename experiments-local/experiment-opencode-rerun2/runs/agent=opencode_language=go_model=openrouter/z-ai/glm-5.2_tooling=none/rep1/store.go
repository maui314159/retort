package main

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// Store manages book persistence in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and initializes the
// books table schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite performs best with a single connection for writes; limiting
	// connections also avoids "database is locked" errors in tests.
	db.SetMaxOpenConns(1)

	s := &Store{db: db}
	if err := s.init(); err != nil {
		_ = db.Close()
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
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);`
	_, err := s.db.Exec(ddl)
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// Close releases the underlying database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns the stored record with its generated ID.
func (s *Store) Create(b *Book) (*Book, error) {
	now := time.Now().UTC().Truncate(time.Second)
	if b.CreatedAt.IsZero() {
		b.CreatedAt = now
	}
	b.UpdatedAt = now

	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

// Get returns a single book by ID. If no book is found, ErrNotFound is returned.
func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`,
		id,
	)
	b, err := scanBook(row)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return b, nil
}

// List returns all books, optionally filtered by author (case-insensitive,
// substring match). Results are ordered by id ascending.
func (s *Store) List(authorFilter string) ([]*Book, error) {
	q := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books`
	var (
		args []any
		rows *sql.Rows
		err  error
	)
	if authorFilter != "" {
		q += " WHERE author LIKE ?"
		args = append(args, "%"+authorFilter+"%")
	}
	q += " ORDER BY id ASC"

	rows, err = s.db.Query(q, args...)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
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
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// Update replaces the mutable fields of the book identified by id. If no book
// exists with that id, ErrNotFound is returned.
func (s *Store) Update(id int64, b *Book) (*Book, error) {
	b.UpdatedAt = time.Now().UTC().Truncate(time.Second)

	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, b.UpdatedAt, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, ErrNotFound
	}
	b.ID = id
	// Re-read to fetch the original created_at.
	stored, err := s.Get(id)
	if err != nil {
		return nil, err
	}
	b.CreatedAt = stored.CreatedAt
	return b, nil
}

// Delete removes a book by ID. If no book exists, ErrNotFound is returned.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// scanner abstracts *sql.Row and *sql.Rows for shared scan logic.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (*Book, error) {
	b := &Book{}
	var createdAt, updatedAt string
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt); err != nil {
		return nil, err
	}
	var err error
	if b.CreatedAt, err = parseTime(createdAt); err != nil {
		return nil, fmt.Errorf("parse created_at: %w", err)
	}
	if b.UpdatedAt, err = parseTime(updatedAt); err != nil {
		return nil, fmt.Errorf("parse updated_at: %w", err)
	}
	return b, nil
}

// parseTime handles the variety of timestamp formats SQLite may return.
func parseTime(v string) (time.Time, error) {
	if v == "" {
		return time.Time{}, nil
	}
	// Trim sub-second precision if present.
	if i := strings.Index(v, "."); i >= 0 {
		v = v[:i]
	}
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		time.RFC3339,
	}
	for _, f := range formats {
		if t, err := time.Parse(f, v); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognized time format %q", v)
}
