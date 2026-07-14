package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned by Store operations that reference a missing book.
var ErrNotFound = errors.New("book not found")

// Store is the SQLite-backed persistence layer for books.
type Store struct {
	db *sql.DB
}

// openStore opens (or creates) the SQLite database at path and ensures the
// schema is in place. The returned store is safe for concurrent use.
func openStore(ctx context.Context, path string) (*Store, error) {
	dsn := fmt.Sprintf("file:%s?cache=shared&mode=rwc&_pragma=foreign_keys(1)", path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	// SQLite serializes writes; a single connection keeps writers ordered
	// while letting readers share the cache.
	db.SetMaxOpenConns(1)
	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping sqlite: %w", err)
	}

	s := &Store{db: db}
	if err := s.init(ctx); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

// init creates the books table if it does not yet exist.
func (s *Store) init(ctx context.Context) error {
	const ddl = `CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	);`
	_, err := s.db.ExecContext(ctx, ddl)
	if err != nil {
		return fmt.Errorf("create table: %w", err)
	}
	return nil
}

// Create inserts a book and returns the row with its assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
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

// List returns every book, optionally filtered by author. When author is
// empty, all rows are returned.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	if author == "" {
		rows, err := s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
		if err != nil {
			return nil, fmt.Errorf("query books: %w", err)
		}
		defer rows.Close()
		return scanBooks(rows)
	}

	rows, err := s.db.QueryContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`, author)
	if err != nil {
		return nil, fmt.Errorf("query books by author: %w", err)
	}
	defer rows.Close()
	return scanBooks(rows)
}

// Get returns the book with the given id, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// Update overwrites the book identified by id with the values in b.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
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

// Delete removes the book with the given id. It is idempotent: deleting a
// missing id returns ErrNotFound so callers can choose the right status.
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

// Close releases the underlying database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

func scanBooks(rows *sql.Rows) ([]Book, error) {
	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows err: %w", err)
	}
	return books, nil
}
