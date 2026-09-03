package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

// Book represents a book record.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks that required fields are present.
func (b Book) validate() error {
	if b.Title == "" {
		return fmt.Errorf("title is required")
	}
	if b.Author == "" {
		return fmt.Errorf("author is required")
	}
	if b.Year < 0 {
		return fmt.Errorf("year must be a non-negative integer")
	}
	return nil
}

// Store is a SQLite-backed book repository.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) a SQLite database at path and initializes the schema.
func NewStore(path string) (*Store, error) {
	if dir := filepath.Dir(path); dir != "" {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return nil, fmt.Errorf("create db dir: %w", err)
		}
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
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
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// Close releases the database connection.
func (s *Store) Close() error { return s.db.Close() }

// CreateBook inserts a book and returns the new record with its ID.
func (s *Store) CreateBook(b Book) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
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

// ListBooks returns all books, optionally filtered by author.
func (s *Store) ListBooks(author string) ([]Book, error) {
	if author != "" {
		rows, err := s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			author,
		)
		if err != nil {
			return nil, fmt.Errorf("query books: %w", err)
		}
		defer rows.Close()
		return scanBooks(rows)
	}
	rows, err := s.db.Query(
		`SELECT id, title, author, year, isbn FROM books ORDER BY id`,
	)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()
	return scanBooks(rows)
}

func scanBooks(rows *sql.Rows) ([]Book, error) {
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows iter: %w", err)
	}
	return books, nil
}

// GetBook returns a single book by ID.
func (s *Store) GetBook(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// UpdateBook updates an existing book by ID.
func (s *Store) UpdateBook(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// DeleteBook removes a book by ID. Returns ErrNotFound if it didn't exist.
func (s *Store) DeleteBook(id int64) error {
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
