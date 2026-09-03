package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// Store wraps a SQLite database connection used by the book service.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures
// the books table exists. When path is ":memory:" a fresh in-memory
// database is created — this is convenient for testing.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping database: %w", err)
	}
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	const ddl = `CREATE TABLE IF NOT EXISTS books (
		id      INTEGER PRIMARY KEY AUTOINCREMENT,
		title   TEXT    NOT NULL,
		author  TEXT    NOT NULL,
		year    INTEGER,
		isbn    TEXT
	);`
	_, err := s.db.Exec(ddl)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}

// Close releases the underlying database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// CreateBook inserts a new book and returns the stored record
// (including the assigned ID).
func (s *Store) CreateBook(in BookInput) (*Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	return &Book{
		ID:     id,
		Title:  in.Title,
		Author: in.Author,
		Year:   in.Year,
		ISBN:   in.ISBN,
	}, nil
}

// GetBook retrieves a single book by ID. It returns (nil, nil) when
// no matching record exists.
func (s *Store) GetBook(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	)
	b, err := scanBook(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return b, nil
}

// ListBooks returns all books, optionally filtered by author. When
// author is a non-empty string only exact-author matches are returned.
func (s *Store) ListBooks(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			author,
		)
	} else {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books ORDER BY id`,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, *b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}

// UpdateBook replaces the mutable fields of the book with the given ID.
// It returns (nil, nil) when no row was updated (i.e. the ID does not
// exist).
func (s *Store) UpdateBook(id int64, in BookInput) (*Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, nil
	}
	return &Book{
		ID:     id,
		Title:  in.Title,
		Author: in.Author,
		Year:   in.Year,
		ISBN:   in.ISBN,
	}, nil
}

// DeleteBook removes the book with the given ID. It returns true when
// a row was actually deleted and false when the ID did not exist.
func (s *Store) DeleteBook(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}

// --- scanning helpers -------------------------------------------------

type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (*Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn)
	if err != nil {
		return nil, fmt.Errorf("scan book: %w", err)
	}
	if year.Valid {
		v := int(year.Int64)
		b.Year = &v
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return &b, nil
}
