package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// Store is the persistence layer for books, backed by SQLite.
type Store struct {
	db *sql.DB
}

// ErrNotFound is returned when a book is not present in the store.
var ErrNotFound = errors.New("book not found")

// NewStore opens (or creates) a SQLite database at path and initializes the schema.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// Enable foreign keys and a reasonable busy timeout for concurrency.
	if _, err := db.ExecContext(context.Background(),
		`PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;`); err != nil {
		db.Close()
		return nil, fmt.Errorf("pragma: %w", err)
	}
	s := &Store{db: db}
	if err := s.initSchema(context.Background()); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) initSchema(ctx context.Context) error {
	const q = `CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	);`
	_, err := s.db.ExecContext(ctx, q)
	if err != nil {
		return fmt.Errorf("init schema: %w", err)
	}
	return nil
}

// Create inserts a new book and returns it with the assigned ID.
func (s *Store) Create(ctx context.Context, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?);`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return nil
}

// List returns all books, optionally filtered by author (exact match).
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id;`,
			author)
	} else {
		rows, err = s.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn FROM books ORDER BY id;`)
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}

// Get returns a single book by ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?;`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, ErrNotFound
		}
		return Book{}, fmt.Errorf("get: %w", err)
	}
	return b, nil
}

// Update updates the given book. Returns ErrNotFound if no row with that ID exists.
func (s *Store) Update(ctx context.Context, b *Book) error {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?;`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID)
	if err != nil {
		return fmt.Errorf("update: %w", err)
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

// Delete removes a book by ID. Returns ErrNotFound if no such row.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?;`, id)
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

// Close closes the underlying database.
func (s *Store) Close() error {
	return s.db.Close()
}
