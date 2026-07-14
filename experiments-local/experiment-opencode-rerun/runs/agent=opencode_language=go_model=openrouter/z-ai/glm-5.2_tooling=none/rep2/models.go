package main

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// Book represents a book record.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year,omitempty"`
	ISBN      string    `json:"isbn,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// validateBook checks required fields and basic constraints.
func validateBook(b *Book) error {
	if strings.TrimSpace(b.Title) == "" {
		return fmt.Errorf("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return fmt.Errorf("author is required")
	}
	if b.Year < 0 || b.Year > 9999 {
		return fmt.Errorf("year must be between 0 and 9999")
	}
	if len(b.Title) > 1024 {
		return fmt.Errorf("title too long (max 1024 chars)")
	}
	if len(b.Author) > 512 {
		return fmt.Errorf("author too long (max 512 chars)")
	}
	if len(b.ISBN) > 32 {
		return fmt.Errorf("isbn too long (max 32 chars)")
	}
	return nil
}

// openDB opens (or creates) the SQLite database and ensures the schema exists.
func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	return db, nil
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER NOT NULL DEFAULT 0,
    isbn TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`
