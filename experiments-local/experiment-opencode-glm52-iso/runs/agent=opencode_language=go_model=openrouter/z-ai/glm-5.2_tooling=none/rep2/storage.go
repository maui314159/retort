package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// Storage wraps the database connection and provides book persistence.
type Storage struct {
	db *sql.DB
}

// NewStorage opens (or creates) a SQLite database at path and initializes the
// schema. Set memory=true to use an in-memory database (useful for tests).
func NewStorage(path string, memory bool) (*Storage, error) {
	dsn := path
	if memory {
		dsn = ":memory:"
	}
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}

	// Enable foreign keys and reasonable busy timeout.
	if _, err := db.Exec("PRAGMA foreign_keys = ON;"); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("pragma: %w", err)
	}

	s := &Storage{db: db}
	if err := s.initSchema(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Storage) initSchema() error {
	const schema = `CREATE TABLE IF NOT EXISTS books (
		id         INTEGER PRIMARY KEY AUTOINCREMENT,
		title      TEXT    NOT NULL,
		author     TEXT    NOT NULL,
		year       INTEGER NOT NULL DEFAULT 0,
		isbn       TEXT    NOT NULL DEFAULT '',
		created_at TEXT    NOT NULL,
		updated_at TEXT    NOT NULL
	);`
	_, err := s.db.Exec(schema)
	return err
}

// Close releases the underlying database handle.
func (s *Storage) Close() error {
	return s.db.Close()
}

// CreateBook inserts a new book and returns the stored record.
func (s *Storage) CreateBook(b *Book) (*Book, error) {
	now := nowRFC3339()
	b.CreatedAt = now
	b.UpdatedAt = now

	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?);`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
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
func (s *Storage) ListBooks(author string) ([]*Book, error) {
	if author != "" {
		rows, err := s.db.Query(
			`SELECT id, title, author, year, isbn, created_at, updated_at
			 FROM books WHERE author = ? ORDER BY id;`, author,
		)
		if err != nil {
			return nil, fmt.Errorf("query: %w", err)
		}
		defer rows.Close()
		return scanBooks(rows)
	}

	rows, err := s.db.Query(
		`SELECT id, title, author, year, isbn, created_at, updated_at
		 FROM books ORDER BY id;`,
	)
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	return scanBooks(rows)
}

// GetBook returns a single book by id. Returns sql.ErrNoRows when missing.
func (s *Storage) GetBook(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at
		 FROM books WHERE id = ?;`, id,
	)
	return scanBook(row)
}

// UpdateBook updates an existing book identified by id. Only the provided
// fields are updated; nil values keep the existing value.
func (s *Storage) UpdateBook(id int64, in *bookInput) (*Book, error) {
	existing, err := s.GetBook(id)
	if err != nil {
		return nil, err
	}
	if in.Title != nil {
		existing.Title = trimSpaces(*in.Title)
	}
	if in.Author != nil {
		existing.Author = trimSpaces(*in.Author)
	}
	if in.Year != nil {
		existing.Year = *in.Year
	}
	if in.ISBN != nil {
		existing.ISBN = *in.ISBN
	}
	existing.UpdatedAt = nowRFC3339()

	_, err = s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		 WHERE id = ?;`,
		existing.Title, existing.Author, existing.Year, existing.ISBN,
		existing.UpdatedAt, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	return existing, nil
}

// DeleteBook removes a book by id. Returns false when no row was affected.
func (s *Storage) DeleteBook(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?;`, id)
	if err != nil {
		return false, fmt.Errorf("delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}

func scanBooks(rows *sql.Rows) ([]*Book, error) {
	books := make([]*Book, 0)
	for rows.Next() {
		b := &Book{}
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}

func scanBook(row *sql.Row) (*Book, error) {
	b := &Book{}
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
		return nil, err
	}
	return b, nil
}
