package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// schema is the DDL used to initialise the books table.
const schema = `
CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER NOT NULL DEFAULT 0,
    isbn  TEXT    NOT NULL DEFAULT ''
);
`

// openDB opens (or creates) the SQLite database at path and ensures the
// schema is in place. It returns the ready-to-use *sql.DB.
func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return db, nil
}

// insertBook persists a new book and returns the row with its assigned ID.
func insertBook(db *sql.DB, b *Book) (*Book, error) {
	res, err := db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

// listBooks returns all books, optionally filtered by author.
func listBooks(db *sql.DB, author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			author,
		)
	} else {
		rows, err = db.Query(
			`SELECT id, title, author, year, isbn FROM books ORDER BY id`,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var out []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		out = append(out, b)
	}
	return out, rows.Err()
}

// getBook fetches a single book by ID.
func getBook(db *sql.DB, id int64) (*Book, error) {
	var b Book
	err := db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("get book: %w", err)
	}
	return &b, nil
}

// updateBook replaces all fields of the book with the given ID.
func updateBook(db *sql.DB, id int64, b *Book) (bool, error) {
	res, err := db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return false, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}

// deleteBook removes the book with the given ID.
func deleteBook(db *sql.DB, id int64) (bool, error) {
	res, err := db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}
