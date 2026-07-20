package main

import (
	"database/sql"
	"errors"

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

// ErrNotFound is returned when a book ID does not exist.
var ErrNotFound = errors.New("book not found")

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (creating if necessary) the SQLite database at path and
// ensures the schema exists.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id     INTEGER PRIMARY KEY AUTOINCREMENT,
			title  TEXT NOT NULL,
			author TEXT NOT NULL,
			year   INTEGER NOT NULL DEFAULT 0,
			isbn   TEXT NOT NULL DEFAULT ''
		)`)
	return err
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a book and returns it with its assigned ID.
func (s *Store) Create(b Book) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// List returns all books, optionally filtered by exact author name.
func (s *Store) List(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`, author)
	} else {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Get fetches a single book by ID, returning ErrNotFound if absent.
func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, err
	}
	return b, nil
}

// Update replaces all fields of the book with the given ID.
func (s *Store) Update(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		return Book{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// Delete removes the book with the given ID.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
