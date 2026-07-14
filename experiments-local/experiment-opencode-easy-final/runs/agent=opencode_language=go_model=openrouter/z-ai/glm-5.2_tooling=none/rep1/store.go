package main

import (
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

type Store struct {
	db *sql.DB
}

func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if _, err := db.Exec(`
CREATE TABLE IF NOT EXISTS books (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	author TEXT NOT NULL,
	year INTEGER NOT NULL DEFAULT 0,
	isbn TEXT NOT NULL DEFAULT '',
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);`); err != nil {
		db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Create(b *Book) (*Book, error) {
	now := time.Now().UTC()
	b.CreatedAt = now
	b.UpdatedAt = now
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?,?,?,?,?,?);`,
		b.Title, b.Author, b.Year, b.ISBN, b.CreatedAt, b.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("lastinsertid: %w", err)
	}
	b.ID = id
	return b, nil
}

func (s *Store) List(author string) ([]*Book, error) {
	rows, err := s.db.Query(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books`+
			cond(author)+` ORDER BY id ASC;`, args(author)...)
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	var out []*Book
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, b)
	}
	return out, rows.Err()
}

func cond(author string) string {
	if author != "" {
		return ` WHERE author = ?`
	}
	return ""
}

func args(author string) []any {
	if author != "" {
		return []any{author}
	}
	return nil
}

func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?;`, id)
	return scanBookRow(row)
}

func (s *Store) Update(id int64, b *Book) (*Book, error) {
	b.UpdatedAt = time.Now().UTC()
	res, err := s.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?;`,
		b.Title, b.Author, b.Year, b.ISBN, b.UpdatedAt, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rowsaffected: %w", err)
	}
	if n == 0 {
		return nil, ErrNotFound
	}
	b.ID = id
	existing, err := s.Get(id)
	if err != nil {
		return nil, err
	}
	b.CreatedAt = existing.CreatedAt
	return b, nil
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?;`, id)
	if err != nil {
		return fmt.Errorf("delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rowsaffected: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func scanBook(rows *sql.Rows) (*Book, error) {
	b := &Book{}
	err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("scan: %w", err)
	}
	return b, nil
}

func scanBookRow(row *sql.Row) (*Book, error) {
	b := &Book{}
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("scan: %w", err)
	}
	return b, nil
}
