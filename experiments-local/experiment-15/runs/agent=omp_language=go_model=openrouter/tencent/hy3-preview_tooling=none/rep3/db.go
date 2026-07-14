package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

// BookStore handles database operations for books
type BookStore struct {
	db *sql.DB
}

// NewBookStore creates a new BookStore and initializes the database
func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Create books table if it doesn't exist
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	`

	if _, err := db.Exec(createTableSQL); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return &BookStore{db: db}, nil
}

// Close closes the database connection
func (s *BookStore) Close() error {
	return s.db.Close()
}

// CreateBook inserts a new book into the database
func (s *BookStore) CreateBook(req CreateBookRequest) (*Book, error) {
	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		req.Title, req.Author, req.Year, req.ISBN,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("failed to get last insert id: %w", err)
	}

	return s.GetBookByID(id)
}

// GetBookByID retrieves a book by its ID
func (s *BookStore) GetBookByID(id int64) (*Book, error) {
	book := &Book{}
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
		id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt)

	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, fmt.Errorf("book with id %d not found", id)
		}
		return nil, fmt.Errorf("failed to query book: %w", err)
	}

	return book, nil
}

// ListBooks retrieves all books, optionally filtered by author
func (s *BookStore) ListBooks(authorFilter string) ([]*Book, error) {
	query := "SELECT id, title, author, year, isbn, created_at, updated_at FROM books"
	args := []interface{}{}

	if authorFilter != "" {
		query += " WHERE author LIKE ?"
		args = append(args, "%"+authorFilter+"%")
	}

	query += " ORDER BY id"

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	books := []*Book{}
	for rows.Next() {
		book := &Book{}
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, book)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return books, nil
}

// UpdateBook updates a book by ID
func (s *BookStore) UpdateBook(id int64, req UpdateBookRequest) (*Book, error) {
	// Check if book exists
	_, err := s.GetBookByID(id)
	if err != nil {
		return nil, err
	}

	// Build dynamic update query
	query := "UPDATE books SET updated_at = CURRENT_TIMESTAMP"
	args := []interface{}{}

	if req.Title != nil {
		query += ", title = ?"
		args = append(args, *req.Title)
	}
	if req.Author != nil {
		query += ", author = ?"
		args = append(args, *req.Author)
	}
	if req.Year != nil {
		query += ", year = ?"
		args = append(args, *req.Year)
	}
	if req.ISBN != nil {
		query += ", isbn = ?"
		args = append(args, *req.ISBN)
	}

	query += " WHERE id = ?"
	args = append(args, id)

	_, err = s.db.Exec(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	return s.GetBookByID(id)
}

// DeleteBook deletes a book by ID
func (s *BookStore) DeleteBook(id int64) error {
	// Check if book exists
	_, err := s.GetBookByID(id)
	if err != nil {
		return err
	}

	_, err = s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	return nil
}
