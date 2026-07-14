package main

import (
	"database/sql"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

type Store struct {
	db *sql.DB
}

func NewStore(dbPath string) (*Store, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	store := &Store{db: db}
	if err := store.initSchema(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to init schema: %w", err)
	}

	return store, nil
}

func (s *Store) initSchema() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err := s.db.Exec(query)
	return err
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) CreateBook(book *Book) error {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	res, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return err
	}
	book.ID = int(id)
	return nil
}

func (s *Store) GetBooks(authorFilter string) ([]Book, error) {
	var query string
	var args []any
	if authorFilter != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?`
		args = append(args, "%"+authorFilter+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
	}

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		var year sql.NullInt64
		var isbn sql.NullString
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
			return nil, err
		}
		if year.Valid {
			b.Year = int(year.Int64)
		}
		if isbn.Valid {
			b.ISBN = isbn.String
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *Store) GetBookByID(id int) (*Book, error) {
	var b Book
	var year sql.NullInt64
	var isbn sql.NullString
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	err := s.db.QueryRow(query, id).Scan(&b.ID, &b.Title, &b.Author, &year, &isbn)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if year.Valid {
		b.Year = int(year.Int64)
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return &b, nil
}

func (s *Store) UpdateBook(id int, book *Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	res, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		return err
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return fmt.Errorf("book not found")
	}
	return nil
}

func (s *Store) DeleteBook(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	res, err := s.db.Exec(query, id)
	if err != nil {
		return err
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return fmt.Errorf("book not found")
	}
	return nil
}
