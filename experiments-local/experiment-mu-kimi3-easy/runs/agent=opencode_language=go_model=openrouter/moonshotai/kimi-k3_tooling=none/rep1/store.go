package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// Book is a single record in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrNotFound is returned when no book exists for a given ID.
var ErrNotFound = errors.New("book not found")

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (creating if necessary) the SQLite database at path and
// ensures the schema exists. Use ":memory:" for an ephemeral database.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	// A single connection keeps in-memory databases consistent across the pool.
	db.SetMaxOpenConns(1)

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(b Book) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	b.ID, err = res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read last insert id: %w", err)
	}
	return b, nil
}

// List returns all books, optionally filtered by exact author name.
func (s *Store) List(author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// Update replaces the fields of the book with the given ID and returns the
// updated record, or ErrNotFound.
func (s *Store) Update(id int64, b Book) (Book, error) {
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

// Delete removes the book with the given ID, or returns ErrNotFound.
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
