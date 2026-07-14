package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned by the Store when a requested row does not exist.
var ErrNotFound = errors.New("book not found")

// Store wraps a SQLite database and exposes the operations the HTTP layer needs.
type Store struct {
	db *sql.DB
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER NOT NULL DEFAULT 0,
    isbn       TEXT    NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`

// NewStore opens (or creates) the SQLite database at dsn and initialises the schema.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	// SQLite serialises writes; a single writer plus a small read pool is plenty.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(0)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the underlying database connection.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a book. The book's ID, CreatedAt and UpdatedAt fields are
// populated from the database before the function returns.
func (s *Store) Create(ctx context.Context, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return s.populateTimestamps(ctx, id, b)
}

// populateTimestamps reads the DB-managed timestamps back into the supplied book.
func (s *Store) populateTimestamps(ctx context.Context, id int64, b *Book) error {
	row := s.db.QueryRowContext(ctx,
		`SELECT created_at, updated_at FROM books WHERE id = ?`, id)
	return row.Scan(&b.CreatedAt, &b.UpdatedAt)
}

// Get fetches a book by id. Returns ErrNotFound if no row matches.
func (s *Store) Get(ctx context.Context, id int64) (*Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn, created_at, updated_at
         FROM books WHERE id = ?`, id)
	var b Book
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("select book: %w", err)
	}
	return &b, nil
}

// List returns all books, optionally filtered by author (exact match).
// If no books match, an empty slice is returned (never nil).
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books WHERE author = ? ORDER BY id`, author)
	} else {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books ORDER BY id`)
	}
	if err != nil {
		return nil, fmt.Errorf("select books: %w", err)
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Update replaces the mutable fields of a book. Returns ErrNotFound if no row
// was updated.
func (s *Store) Update(ctx context.Context, id int64, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?, updated_at = CURRENT_TIMESTAMP
          WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return s.populateTimestamps(ctx, id, b)
}

// Delete removes a book by id. Returns ErrNotFound if no row was deleted.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
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
