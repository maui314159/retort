package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

// ErrNotFound is returned when a book lookup yields no rows.
var ErrNotFound = errors.New("book not found")

// Store wraps the database connection and provides CRUD operations.
type Store struct {
	db *sql.DB
}

// NewStore opens (creating if necessary) the SQLite database at path
// and initializes the schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite3", path+"?_busy_timeout=5000&_fk=1")
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	// SQLite handles concurrent reads well, but for the test suite we use
	// a single connection so that writes serialize cleanly.
	db.SetMaxOpenConns(1)
	s := &Store{db: db}
	if err := s.init(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) init() error {
	const schema = `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err := s.db.Exec(schema)
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns it with the assigned id.
func (s *Store) Create(title, author string, year *int, isbn string) (Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return Book{ID: id, Title: title, Author: author, Year: year, ISBN: isbn}, nil
}

// List returns all books. When author is non-empty, results are filtered
// to books whose author matches (case-insensitive, exact).
func (s *Store) List(author string) ([]Book, error) {
	rows, err := s.db.Query(
		"SELECT id, title, author, year, isbn FROM books ORDER BY id")
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return scanBooks(rows, author)
}

// Get returns a single book by id.
func (s *Store) Get(id int64) (Book, error) {
	row := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	b, err := scanBook(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, ErrNotFound
		}
		return Book{}, err
	}
	return b, nil
}

// Update replaces the title/author/year/isbn of the book with the given id.
// Only fields present (non-nil) in inp are updated.
func (s *Store) Update(id int64, inp bookInput) (Book, error) {
	// Ensure the book exists first so we can return ErrNotFound.
	existing, err := s.Get(id)
	if err != nil {
		return Book{}, err
	}
	if inp.Title != nil {
		existing.Title = *inp.Title
	}
	if inp.Author != nil {
		existing.Author = *inp.Author
	}
	if inp.Year != nil {
		existing.Year = inp.Year
	}
	if inp.ISBN != nil {
		existing.ISBN = *inp.ISBN
	}
	_, err = s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		existing.Title, existing.Author, existing.Year, existing.ISBN, id)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	return existing, nil
}

// Delete removes a book by id. It is idempotent: deleting a missing id
// returns nil.
func (s *Store) Delete(id int64) error {
	_, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	return nil
}

type rowScanner interface {
	Scan(dest ...interface{}) error
}

func scanBook(row rowScanner) (Book, error) {
	var b Book
	var year sql.NullInt64
	var isbn sql.NullString
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return b, nil
}

func scanBooks(rows *sql.Rows, authorFilter string) ([]Book, error) {
	defer rows.Close()
	var books []Book
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		if authorFilter != "" && !equalFoldASCII(b.Author, authorFilter) {
			continue
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// equalFoldASCII performs a case-insensitive ASCII comparison without
// importing strings just for this niche need.
func equalFoldASCII(a, b string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := 0; i < len(a); i++ {
		ca, cb := a[i], b[i]
		if 'A' <= ca && ca <= 'Z' {
			ca += 'a' - 'A'
		}
		if 'A' <= cb && cb <= 'Z' {
			cb += 'a' - 'A'
		}
		if ca != cb {
			return false
		}
	}
	return true
}
