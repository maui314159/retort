package main

import (
	"database/sql"
	"fmt"
)

// Store defines the persistence operations for books.
type Store interface {
	Create(b *Book) (*Book, error)
	GetAll(author string) ([]*Book, error)
	GetByID(id int64) (*Book, error)
	Update(id int64, b *Book) (*Book, error)
	Delete(id int64) error
}

// sqliteStore implements Store using an embedded SQLite database.
type sqliteStore struct {
	db *sql.DB
}

// NewSQLiteStore opens (or creates) a SQLite database at path and
// initialises the schema. Pass ":memory:" or a filesystem path.
func NewSQLiteStore(path string) (*sqliteStore, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	schema := `
CREATE TABLE IF NOT EXISTS books (
	id    INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT    NOT NULL,
	author TEXT   NOT NULL,
	year  INTEGER NOT NULL DEFAULT 0,
	isbn  TEXT    NOT NULL DEFAULT ''
);`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}

	return &sqliteStore{db: db}, nil
}

// Close releases the underlying database connection.
func (s *sqliteStore) Close() error {
	return s.db.Close()
}

// Create inserts a new book and returns it with the generated ID.
func (s *sqliteStore) Create(b *Book) (*Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
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

// GetAll returns every book, optionally filtered by author. An empty
// author string returns all books.
func (s *sqliteStore) GetAll(author string) ([]*Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var (
		args []any
		rows *sql.Rows
		err  error
	)
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err = s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		b := &Book{}
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}

// GetByID returns a single book by its ID.
func (s *sqliteStore) GetByID(id int64) (*Book, error) {
	b := &Book{}
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		return nil, err
	}
	return b, nil
}

// Update replaces the mutable fields of the book identified by id.
func (s *sqliteStore) Update(id int64, b *Book) (*Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, sql.ErrNoRows
	}
	b.ID = id
	return b, nil
}

// Delete removes the book identified by id.
func (s *sqliteStore) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}
