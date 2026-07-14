package main

import (
	"database/sql"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}
	store := &BookStore{db: db}
	if err := store.migrate(); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return store, nil
}

func (s *BookStore) Close() error {
	return s.db.Close()
}

func (s *BookStore) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id    INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT    NOT NULL,
			author TEXT   NOT NULL,
			year  INTEGER,
			isbn  TEXT
		)
	`)
	return err
}

func (s *BookStore) Create(b *Book) (*Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, nullInt(b.Year), nullString(b.ISBN),
	)
	if err != nil {
		return nil, fmt.Errorf("insert: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

func (s *BookStore) List(author string) ([]Book, error) {
	var rows *sql.Rows
	var err error
	if author != "" {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		var year sql.NullInt64
		var isbn sql.NullString
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
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

func (s *BookStore) Get(id int64) (*Book, error) {
	var b Book
	var year sql.NullInt64
	var isbn sql.NullString
	err := s.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.ID, &b.Title, &b.Author, &year, &isbn)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("query row: %w", err)
	}
	if year.Valid {
		b.Year = int(year.Int64)
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return &b, nil
}

func (s *BookStore) Update(id int64, b *Book) (*Book, error) {
	res, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, nullInt(b.Year), nullString(b.ISBN), id,
	)
	if err != nil {
		return nil, fmt.Errorf("update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return nil, nil
	}
	b.ID = id
	return b, nil
}

func (s *BookStore) Delete(id int64) (bool, error) {
	res, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return false, fmt.Errorf("delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("rows affected: %w", err)
	}
	return n > 0, nil
}

func nullInt(v int) sql.NullInt64 {
	return sql.NullInt64{Int64: int64(v), Valid: v != 0}
}

func nullString(v string) sql.NullString {
	return sql.NullString{String: v, Valid: v != ""}
}
