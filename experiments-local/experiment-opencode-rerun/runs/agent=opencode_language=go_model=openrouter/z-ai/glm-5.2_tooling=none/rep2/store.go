package main

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

var errBookNotFound = errors.New("book not found")

// createBook inserts a new book and returns the populated record.
func createBook(db *sql.DB, b *Book) (*Book, error) {
	now := time.Now().UTC()
	b.CreatedAt = now
	b.UpdatedAt = now
	res, err := db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("lastInsertId: %w", err)
	}
	b.ID = id
	return b, nil
}

// listBooks returns all books, optionally filtered by author (case-insensitive contains).
func listBooks(db *sql.DB, authorFilter string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books`
	var rows *sql.Rows
	var err error
	if strings.TrimSpace(authorFilter) != "" {
		q += ` WHERE author LIKE ? ORDER BY id`
		rows, err = db.Query(q, "%"+authorFilter+"%")
	} else {
		q += ` ORDER BY id`
		rows, err = db.Query(q)
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	return scanBooks(rows)
}

// getBook returns a single book by ID.
func getBook(db *sql.DB, id int64) (*Book, error) {
	row := db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`, id,
	)
	var b Book
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, errBookNotFound
		}
		return nil, fmt.Errorf("scan: %w", err)
	}
	return &b, nil
}

// updateBook updates an existing book by ID. Returns errBookNotFound if missing.
func updateBook(db *sql.DB, id int64, b *Book) (*Book, error) {
	existing, err := getBook(db, id)
	if err != nil {
		return nil, err
	}
	// Preserve created_at; refresh updated_at.
	b.ID = id
	b.CreatedAt = existing.CreatedAt
	b.UpdatedAt = time.Now().UTC()
	res, err := db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, b.UpdatedAt, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rowsAffected: %w", err)
	}
	if n == 0 {
		return nil, errBookNotFound
	}
	return b, nil
}

// deleteBook removes a book by ID. Returns errBookNotFound if it didn't exist.
func deleteBook(db *sql.DB, id int64) error {
	res, err := db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rowsAffected: %w", err)
	}
	if n == 0 {
		return errBookNotFound
	}
	return nil
}

func scanBooks(rows *sql.Rows) ([]Book, error) {
	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}
	return books, nil
}
