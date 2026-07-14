package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dsn string) (*BookStore, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	if err := migrate(db); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}

	return &BookStore{db: db}, nil
}

func migrate(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			title      TEXT NOT NULL,
			author     TEXT NOT NULL,
			year       INTEGER,
			isbn       TEXT DEFAULT '',
			created_at TEXT NOT NULL DEFAULT '',
			updated_at TEXT NOT NULL DEFAULT ''
		)
	`)
	return err
}

func (s *BookStore) Close() error {
	return s.db.Close()
}

func (s *BookStore) Create(b *Book) error {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
	)
	if err != nil {
		return fmt.Errorf("insert: %w", err)
	}
	id, _ := res.LastInsertId()
	b.ID = id
	return nil
}

func (s *BookStore) List(author string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if author != "" {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ?`, author)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn, created_at, updated_at FROM books`)
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *BookStore) Get(id int64) (*Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	return &b, nil
}

func (s *BookStore) Update(id int64, b *Book) (bool, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, b.UpdatedAt, id,
	)
	if err != nil {
		return false, fmt.Errorf("update: %w", err)
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func (s *BookStore) Delete(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return false, fmt.Errorf("delete: %w", err)
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}
