package main

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // registers "sqlite" driver
)

// ErrNotFound is returned when a book is not present in the store.
var ErrNotFound = errors.New("book not found")

// Store is the persistence layer for books, backed by SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures
// the books schema exists.
func NewStore(path string) (*Store, error) {
	dsn := fmt.Sprintf("file:%s?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)", path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping sqlite: %w", err)
	}
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return s, nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

func (s *Store) migrate() error {
	_, err := s.db.Exec(`
CREATE TABLE IF NOT EXISTS books (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  title  TEXT NOT NULL,
  author TEXT NOT NULL,
  year   INTEGER NOT NULL DEFAULT 0,
  isbn   TEXT NOT NULL DEFAULT ''
);`)
	return err
}

// Create inserts a new book and returns it with the assigned ID.
func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?);`,
		strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN))
	if err != nil {
		return fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	return nil
}

// Get returns a single book by ID, or ErrNotFound.
func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?;`, id)
	b := &Book{}
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("scan: %w", err)
	}
	return b, nil
}

// List returns all books, optionally filtered by author (case-insensitive).
func (s *Store) List(author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var rows *sql.Rows
	var err error
	if strings.TrimSpace(author) != "" {
		q += ` WHERE lower(author) = lower(?) ORDER BY id;`
		rows, err = s.db.Query(q, strings.TrimSpace(author))
	} else {
		q += ` ORDER BY id;`
		rows, err = s.db.Query(q)
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan row: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	if books == nil {
		books = []Book{}
	}
	return books, nil
}

// Update replaces the fields of an existing book. Returns ErrNotFound if absent.
func (s *Store) Update(id int64, b *Book) error {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?;`,
		strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), b.Year, strings.TrimSpace(b.ISBN), id)
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
	b.ID = id
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	b.ISBN = strings.TrimSpace(b.ISBN)
	return nil
}

// Delete removes a book. Returns ErrNotFound if it did not exist.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?;`, id)
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
