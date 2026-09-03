package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book is not found in the database.
var ErrNotFound = errors.New("book not found")

// Storage provides CRUD operations for books backed by a SQLite database.
type Storage struct {
	db *sql.DB
}

// NewStorage opens (or creates) a SQLite database at the given path and
// ensures the books table exists. Pass ":memory:" for an in-memory database.
func NewStorage(path string) (*Storage, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	schema := `CREATE TABLE IF NOT EXISTS books (
		id    INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year  INTEGER,
		isbn  TEXT
	);`

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}

	return &Storage{db: db}, nil
}

// Close closes the underlying database connection.
func (s *Storage) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns it with the generated ID.
func (s *Storage) Create(b Book) (Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, nullInt(b.Year), nullStr(b.ISBN),
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}

	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("get last insert id: %w", err)
	}

	b.ID = id
	return b, nil
}

// GetAll returns all books, optionally filtered by author. When author is
// non-empty only books whose author matches exactly are returned.
func (s *Storage) GetAll(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)

	if author != "" {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author = ?",
			author,
		)
	} else {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books",
		)
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// GetByID returns a single book by its ID. If no book exists with the given
// ID, ErrNotFound is returned.
func (s *Storage) GetByID(id int64) (Book, error) {
	row := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?",
		id,
	)
	b, err := scanBookRow(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// Update replaces all fields of the book identified by id. If no book exists
// with the given ID, ErrNotFound is returned.
func (s *Storage) Update(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, nullInt(b.Year), nullStr(b.ISBN), id,
	)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}

	rows, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if rows == 0 {
		return Book{}, ErrNotFound
	}

	b.ID = id
	return b, nil
}

// Delete removes the book identified by id. If no book exists with the given
// ID, ErrNotFound is returned.
func (s *Storage) Delete(id int64) error {
	res, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
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

// --- helpers ---

func nullInt(v int) any {
	if v == 0 {
		return nil
	}
	return v
}

func nullStr(v string) any {
	if v == "" {
		return nil
	}
	return v
}

func scanBook(rows *sql.Rows) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := rows.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return Book{}, fmt.Errorf("scan book: %w", err)
	}
	if year.Valid {
		b.Year = int(year.Int64)
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return b, nil
}

func scanBookRow(row *sql.Row) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return Book{}, err
	}
	if year.Valid {
		b.Year = int(year.Int64)
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return b, nil
}
