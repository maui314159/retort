package main

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Storage struct {
	db *sql.DB
}

func NewStorage(dbPath string) (*Storage, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	s := &Storage{db: db}
	if err := s.initSchema(); err != nil {
		return nil, fmt.Errorf("failed to initialize schema: %w", err)
	}

	return s, nil
}

func (s *Storage) initSchema() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT,
		created_at DATETIME NOT NULL,
		updated_at DATETIME NOT NULL
	);
	`
	_, err := s.db.Exec(query)
	return err
}

func (s *Storage) CreateBook(book *Book) error {
	now := time.Now()
	book.CreatedAt = now
	book.UpdatedAt = now

	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN, now, now,
	)
	if err != nil {
		return err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return err
	}
	book.ID = id
	return nil
}

func (s *Storage) GetAllBooks(authorFilter string) ([]*Book, error) {
	query := "SELECT id, title, author, year, isbn, created_at, updated_at FROM books"
	args := []interface{}{}

	if authorFilter != "" {
		query += " WHERE author LIKE ?"
		args = append(args, "%"+authorFilter+"%")
	}

	query += " ORDER BY id"

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := []*Book{}
	for rows.Next() {
		book := &Book{}
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt); err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func (s *Storage) GetBookByID(id int64) (*Book, error) {
	book := &Book{}
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
		id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt)

	if errors.Is(err, sql.ErrNoRows) {
		return nil, fmt.Errorf("book not found")
	}
	return book, err
}

func (s *Storage) UpdateBook(id int64, updates *UpdateBookRequest) error {
	book, err := s.GetBookByID(id)
	if err != nil {
		return err
	}

	if updates.Title != nil {
		book.Title = *updates.Title
	}
	if updates.Author != nil {
		book.Author = *updates.Author
	}
	if updates.Year != nil {
		book.Year = *updates.Year
	}
	if updates.ISBN != nil {
		book.ISBN = *updates.ISBN
	}
	book.UpdatedAt = time.Now()

	_, err = s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, book.UpdatedAt, id,
	)
	return err
}

func (s *Storage) DeleteBook(id int64) error {
	result, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected == 0 {
		return fmt.Errorf("book not found")
	}
	return nil
}

func (s *Storage) Close() error {
	return s.db.Close()
}
