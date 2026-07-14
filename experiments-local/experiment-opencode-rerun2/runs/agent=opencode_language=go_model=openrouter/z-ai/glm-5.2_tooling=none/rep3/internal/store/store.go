package store

import (
	"database/sql"
	"fmt"

	"bookapi/internal/models"

	_ "modernc.org/sqlite"
)

// Store is a SQLite-backed book repository.
type Store struct {
	db *sql.DB
}

// Open opens (and migrates) the SQLite database at path.
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// Single-writer mode reduces SQLITE_BUSY errors for embedded use.
	if _, err := db.Exec(`PRAGMA journal_mode=WAL;`); err != nil {
		db.Close()
		return nil, fmt.Errorf("set journal_mode: %w", err)
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
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	);`
	_, err := s.db.Exec(ddl)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a book and returns the stored record with its new ID.
func (s *Store) Create(in models.BookInput) (models.Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN,
	)
	if err != nil {
		return models.Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return models.Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return models.Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Get returns a single book by id.
func (s *Store) Get(id int64) (models.Book, error) {
	var b models.Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`,
		id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return models.Book{}, ErrNotFound
	}
	if err != nil {
		return models.Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// List returns all books, optionally filtered by author (exact, case-sensitive).
func (s *Store) List(author string) ([]models.Book, error) {
	if author != "" {
		rows, err := s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			author,
		)
		return scanBooks(rows, err)
	}
	rows, err := s.db.Query(
		`SELECT id, title, author, year, isbn FROM books ORDER BY id`,
	)
	return scanBooks(rows, err)
}

func scanBooks(rows *sql.Rows, err error) ([]models.Book, error) {
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()
	var books []models.Book
	for rows.Next() {
		var b models.Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return books, nil
}

// Update replaces the stored book identified by id with the provided input.
func (s *Store) Update(id int64, in models.BookInput) (models.Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id,
	)
	if err != nil {
		return models.Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return models.Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return models.Book{}, ErrNotFound
	}
	return models.Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Delete removes the book identified by id.
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
