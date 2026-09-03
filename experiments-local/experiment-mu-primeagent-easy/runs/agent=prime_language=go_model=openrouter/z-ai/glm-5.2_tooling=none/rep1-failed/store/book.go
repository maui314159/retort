package store

import (
	"database/sql"
	"fmt"

	"github.com/example/bookapi/model"

	_ "modernc.org/sqlite"
)

// InitSchema creates the books table if it does not already exist.
func InitSchema(db *sql.DB) error {
	const q = `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	);`
	_, err := db.Exec(q)
	return err
}

// BookStore provides CRUD operations against a SQLite database.
type BookStore struct {
	db *sql.DB
}

// NewBookStore returns a BookStore backed by the given database handle.
func NewBookStore(db *sql.DB) *BookStore {
	return &BookStore{db: db}
}

// Create inserts a new book and returns the book with its assigned ID.
func (s *BookStore) Create(b model.BookInput) (model.Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return model.Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return model.Book{}, fmt.Errorf("last insert id: %w", err)
	}
	return model.Book{
		ID:     int(id),
		Title:  b.Title,
		Author: b.Author,
		Year:   b.Year,
		ISBN:   b.ISBN,
	}, nil
}

// List returns all books, optionally filtered by author (exact match on
// the given author name; an empty author returns every book).
func (s *BookStore) List(author string) ([]model.Book, error) {
	if author != "" {
		return s.queryBooks("SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id", author)
	}
	return s.queryBooks("SELECT id, title, author, year, isbn FROM books ORDER BY id")
}

func (s *BookStore) queryBooks(q string, args ...any) ([]model.Book, error) {
	rows, err := s.db.Query(q, args...)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []model.Book
	for rows.Next() {
		var b model.Book
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

// Get returns the book with the given ID. If no book is found, the second
// return value is false.
func (s *BookStore) Get(id int) (model.Book, bool, error) {
	row := s.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	var b model.Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return model.Book{}, false, nil
	}
	if err != nil {
		return model.Book{}, false, fmt.Errorf("get book: %w", err)
	}
	return b, true, nil
}

// Update replaces the title, author, year and isbn of the book with the
// given ID. It returns the updated book and a boolean indicating whether
// a row was actually modified.
func (s *BookStore) Update(id int, b model.BookInput) (model.Book, bool, error) {
	res, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return model.Book{}, false, fmt.Errorf("update book: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return model.Book{}, false, fmt.Errorf("rows affected: %w", err)
	}
	if rows == 0 {
		return model.Book{}, false, nil
	}
	return model.Book{
		ID:     id,
		Title:  b.Title,
		Author: b.Author,
		Year:   b.Year,
		ISBN:   b.ISBN,
	}, true, nil
}

// Delete removes the book with the given ID. It returns true when a row was
// actually deleted.
func (s *BookStore) Delete(id int) (bool, error) {
	res, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return rows > 0, nil
}
