package database

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Published int       `json:"published_year,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type DB struct {
	*sql.DB
}

func NewDB(dataSourceName string) (*DB, error) {
	db, err := sql.Open("sqlite3", dataSourceName)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping database: %w", err)
	}

	if err := initSchema(db); err != nil {
		return nil, fmt.Errorf("init schema: %w", err)
	}

	return &DB{db}, nil
}

func initSchema(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		published_year INTEGER,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);

	CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
	CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
	CREATE INDEX IF NOT EXISTS idx_books_published_year ON books(published_year);
	`

	_, err := db.Exec(schema)
	return err
}

func (db *DB) CreateBook(book *Book) error {
	now := time.Now()
	book.CreatedAt = now
	book.UpdatedAt = now

	query := `INSERT INTO books (title, author, published_year, created_at, updated_at) VALUES (?, ?, ?, ?, ?)`
	result, err := db.Exec(query, book.Title, book.Author, book.Published, book.CreatedAt, book.UpdatedAt)
	if err != nil {
		return fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return fmt.Errorf("get last insert id: %w", err)
	}
	book.ID = id
	return nil
}

func (db *DB) GetBookByID(id int64) (*Book, error) {
	query := `SELECT id, title, author, published_year, created_at, updated_at FROM books WHERE id = ?`
	row := db.QueryRow(query, id)

	book := &Book{}
	err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Published, &book.CreatedAt, &book.UpdatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("scan book: %w", err)
	}
	return book, nil
}

func (db *DB) GetBooks(limit, offset int) ([]*Book, error) {
	query := `SELECT id, title, author, published_year, created_at, updated_at FROM books ORDER BY created_at DESC LIMIT ? OFFSET ?`
	rows, err := db.Query(query, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		book := &Book{}
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Published, &book.CreatedAt, &book.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, book)
	}
	return books, rows.Err()
}

func (db *DB) UpdateBook(book *Book) error {
	book.UpdatedAt = time.Now()
	query := `UPDATE books SET title = ?, author = ?, published_year = ?, updated_at = ? WHERE id = ?`
	result, err := db.Exec(query, book.Title, book.Author, book.Published, book.UpdatedAt, book.ID)
	if err != nil {
		return fmt.Errorf("update book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (db *DB) DeleteBook(id int64) error {
	query := `DELETE FROM books WHERE id = ?`
	result, err := db.Exec(query, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (db *DB) CountBooks() (int, error) {
	var count int
	err := db.QueryRow(`SELECT COUNT(*) FROM books`).Scan(&count)
	return count, err
}

func (db *DB) HealthCheck() error {
	return db.Ping()
}
