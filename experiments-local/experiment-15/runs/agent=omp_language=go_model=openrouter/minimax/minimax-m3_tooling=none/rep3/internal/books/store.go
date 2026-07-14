package books

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	// Pure-Go SQLite driver; registers itself as "sqlite".
	_ "modernc.org/sqlite"
)

// Store is the persistence interface for books. It is implemented by
// SQLiteStore but kept small so tests can stub it out if needed.
type Store interface {
	Create(ctx context.Context, b *Book) error
	Get(ctx context.Context, id int64) (*Book, error)
	List(ctx context.Context, author string) ([]*Book, error)
	Update(ctx context.Context, id int64, b *Book) error
	Delete(ctx context.Context, id int64) error
	Close() error
}

// SQLiteStore persists books in a single SQLite database file.
type SQLiteStore struct {
	db *sql.DB
}

// Open returns a SQLiteStore backed by the given file path. Use ":memory:"
// for an in-memory database, which is convenient for tests.
func Open(path string) (*SQLiteStore, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite is single-writer; limit connections to avoid spurious
	// "database is locked" errors when serving concurrent requests.
	db.SetMaxOpenConns(1)

	s := &SQLiteStore{db: db}
	if err := s.migrate(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return s, nil
}

func (s *SQLiteStore) migrate() error {
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
	_, err := s.db.Exec(ddl)
	return err
}

// Close releases the underlying database connection.
func (s *SQLiteStore) Close() error { return s.db.Close() }

// Create inserts b and assigns it a new ID.
func (s *SQLiteStore) Create(ctx context.Context, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
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
	return nil
}

// Get returns a single book by ID, or ErrNotFound if no row matches.
func (s *SQLiteStore) Get(ctx context.Context, id int64) (*Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	)
	return scanBook(row)
}

// List returns all books, optionally filtered by author (exact match).
// An empty author returns every book.
func (s *SQLiteStore) List(ctx context.Context, author string) ([]*Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author == "" {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	} else {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			author,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var out []*Book
	for rows.Next() {
		b, err := scanBook(rows)
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

// Update replaces the book with the given ID. Returns ErrNotFound if
// no row matches.
func (s *SQLiteStore) Update(ctx context.Context, id int64, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
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
	b.ID = id
	return nil
}

// Delete removes the book with the given ID. Returns ErrNotFound if
// no row matches.
func (s *SQLiteStore) Delete(ctx context.Context, id int64) error {
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

// rowScanner is satisfied by both *sql.Row and *sql.Rows, so scanBook
// can be reused for Get and List without duplicating the column list.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(r rowScanner) (*Book, error) {
	var b Book
	if err := r.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("scan book: %w", err)
	}
	return &b, nil
}
