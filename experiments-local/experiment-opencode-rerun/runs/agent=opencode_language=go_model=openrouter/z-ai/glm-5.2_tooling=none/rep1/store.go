package main

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

// Book represents a book record in the collection.
type Book struct {
	ID        int64  `json:"id"`
	Title     string `json:"title"`
	Author    string `json:"author"`
	Year      int    `json:"year,omitempty"`
	ISBN      string `json:"isbn,omitempty"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// Store is the SQLite-backed book repository.
type Store struct {
	db *sql.DB
}

// ErrNotFound is returned when no book matches the given id.
var ErrNotFound = errors.New("book not found")

// ErrInvalid is returned when input validation fails.
var ErrInvalid = errors.New("invalid book data")

// NewStore opens the SQLite database at path and initializes the schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite performs better with a small connection pool.
	db.SetMaxOpenConns(1)

	s := &Store{db: db}
	if err := s.init(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

func (s *Store) init() error {
	const ddl = `CREATE TABLE IF NOT EXISTS books (
		id         INTEGER PRIMARY KEY AUTOINCREMENT,
		title      TEXT    NOT NULL,
		author     TEXT    NOT NULL,
		year       INTEGER NOT NULL DEFAULT 0,
		isbn       TEXT    NOT NULL DEFAULT '',
		created_at TEXT    NOT NULL,
		updated_at TEXT    NOT NULL
	);
	CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);`
	_, err := s.db.Exec(ddl)
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// validate returns ErrInvalid if required fields are missing.
func (b *Book) validate() error {
	if b.Title == "" || b.Author == "" {
		return ErrInvalid
	}
	return nil
}

// Create inserts a new book and returns the stored record with its id.
func (s *Store) Create(b *Book) (*Book, error) {
	if err := b.validate(); err != nil {
		return nil, err
	}
	now := time.Now().UTC().Format(time.RFC3339)
	b.CreatedAt = now
	b.UpdatedAt = now

	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?)`,
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

// Get retrieves a single book by id.
func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at
		 FROM books WHERE id = ?`, id,
	)
	b := &Book{}
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("get: %w", err)
	}
	return b, nil
}

// List returns all books, optionally filtered by author.
func (s *Store) List(author string) ([]*Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author == "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn, created_at, updated_at
			 FROM books ORDER BY id`)
	} else {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn, created_at, updated_at
			 FROM books WHERE author = ? ORDER BY id`, author)
	}
	if err != nil {
		return nil, fmt.Errorf("list: %w", err)
	}
	defer rows.Close()

	var out []*Book
	for rows.Next() {
		b := &Book{}
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		out = append(out, b)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// Update overwrites the mutable fields of a book identified by id.
func (s *Store) Update(id int64, b *Book) (*Book, error) {
	if err := b.validate(); err != nil {
		return nil, err
	}
	now := time.Now().UTC().Format(time.RFC3339)

	res, err := s.db.Exec(
		`UPDATE books
		 SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		 WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, now, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, ErrNotFound
	}
	b.ID = id
	b.UpdatedAt = now
	// Preserve created_at from the existing record.
	existing, err := s.Get(id)
	if err != nil {
		return nil, err
	}
	b.CreatedAt = existing.CreatedAt
	return b, nil
}

// Delete removes a book by id. It returns ErrNotFound if no row was affected.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete: %w", err)
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
