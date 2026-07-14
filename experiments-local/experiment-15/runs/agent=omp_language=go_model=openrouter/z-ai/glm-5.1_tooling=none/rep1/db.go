package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type BookRepo struct {
	db *sql.DB
}

func NewBookRepo(dsn string) (*BookRepo, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	repo := &BookRepo{db: db}
	if err := repo.migrate(); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return repo, nil
}

func (r *BookRepo) Close() error { return r.db.Close() }

func (r *BookRepo) migrate() error {
	_, err := r.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id     INTEGER PRIMARY KEY AUTOINCREMENT,
			title  TEXT NOT NULL,
			author TEXT NOT NULL,
			year   INTEGER DEFAULT 0,
			isbn   TEXT DEFAULT ''
		)
	`)
	return err
}

func (r *BookRepo) Create(b BookInput) (*Book, error) {
	res, err := r.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return nil, err
	}
	id, _ := res.LastInsertId()
	return &Book{ID: id, Title: b.Title, Author: b.Author, Year: b.Year, ISBN: b.ISBN}, nil
}

func (r *BookRepo) List(author string) ([]Book, error) {
	if author != "" {
		rows, err := r.db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		return scanBooks(rows)
	}
	rows, err := r.db.Query("SELECT id, title, author, year, isbn FROM books")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanBooks(rows)
}

func (r *BookRepo) Get(id int64) (*Book, error) {
	row := r.db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
	var b Book
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		return nil, err
	}
	return &b, nil
}

func (r *BookRepo) Update(id int64, b BookInput) (*Book, error) {
	_, err := r.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return nil, err
	}
	return r.Get(id)
}

func (r *BookRepo) Delete(id int64) error {
	_, err := r.db.Exec("DELETE FROM books WHERE id = ?", id)
	return err
}

func scanBooks(rows *sql.Rows) ([]Book, error) {
	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, nil
}
