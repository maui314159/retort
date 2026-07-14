// Package store persists books in SQLite.
//
// The store is safe for concurrent use: a single *sql.DB is shared and all
// methods use parameterised queries. It exposes a small surface — Open,
// Create, Get, List, Update, Delete — and is the only place that knows the
// SQL schema.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"books/internal/book"

	_ "modernc.org/sqlite" // pure-Go SQLite driver
)

// ErrNotFound is returned when a lookup by ID has no row. The API layer
// translates it into HTTP 404.
var ErrNotFound = errors.New("book not found")

// Store wraps an *sql.DB and exposes book-shaped operations.
type Store struct {
	db *sql.DB
}

// Open returns a Store backed by the given SQLite file path. The connection
// pool is configured for a small server (max open 1 keeps writes serial, which
// is more than enough for an embedded book collection and avoids the
// "database is locked" surprise from a busy writer).
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	db.SetMaxOpenConns(1)
	if err := db.PingContext(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping sqlite: %w", err)
	}
	s := &Store{db: db}
	if err := s.migrate(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return s, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

// DB exposes the raw *sql.DB for tests that need to inspect schema state.
func (s *Store) DB() *sql.DB { return s.db }

func (s *Store) migrate(ctx context.Context) error {
	const ddl = `
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER NOT NULL DEFAULT 0,
    isbn   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`
	_, err := s.db.ExecContext(ctx, ddl)
	return err
}

// Create inserts a book and returns it with the assigned ID populated.
func (s *Store) Create(ctx context.Context, in book.Input) (book.Book, error) {
	n := in.Normalize()
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		n.Title, n.Author, n.Year, n.ISBN,
	)
	if err != nil {
		return book.Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return book.Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return book.Book{
		ID:     id,
		Title:  n.Title,
		Author: n.Author,
		Year:   n.Year,
		ISBN:   n.ISBN,
	}, nil
}

// Get fetches a book by its ID. Returns ErrNotFound if no row exists.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	return scanRow(row)
}

// List returns all books, optionally filtered by a case-insensitive substring
// match on author. An empty authorFilter returns every book.
//
// Sorting is by id ASC so the order is stable across calls — clients can rely
// on the first row being the oldest book.
func (s *Store) List(ctx context.Context, authorFilter string) ([]book.Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if authorFilter = strings.TrimSpace(authorFilter); authorFilter != "" {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn
               FROM books
              WHERE LOWER(author) LIKE LOWER(?)
              ORDER BY id ASC`,
			"%"+authorFilter+"%",
		)
	} else {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books ORDER BY id ASC`)
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var out []book.Book
	for rows.Next() {
		b, err := scanRow(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return out, nil
}

// Update replaces the mutable fields of the book with the given ID. The ID
// itself is preserved. Returns ErrNotFound if the book does not exist.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	n := in.Normalize()
	res, err := s.db.ExecContext(ctx,
		`UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?
          WHERE id = ?`,
		n.Title, n.Author, n.Year, n.ISBN, id,
	)
	if err != nil {
		return book.Book{}, fmt.Errorf("update book: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return book.Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if rows == 0 {
		return book.Book{}, ErrNotFound
	}
	return s.Get(ctx, id)
}

// Delete removes a book by ID. Returns ErrNotFound if the book does not exist.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if rows == 0 {
		return ErrNotFound
	}
	return nil
}

// rowScanner is implemented by both *sql.Row and *sql.Rows, letting Get and
// List share a single row-decoding helper.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanRow(r rowScanner) (book.Book, error) {
	var b book.Book
	if err := r.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return book.Book{}, ErrNotFound
		}
		return book.Book{}, fmt.Errorf("scan book: %w", err)
	}
	return b, nil
}
