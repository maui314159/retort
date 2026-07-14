package database

import (
	"database/sql"
	"errors"
	"fmt"
	"log"
	"time"

	"bookapi/models"

	"github.com/google/uuid"
)

type BookStoreDB struct {
	db *sql.DB
}

func NewBookStore(db *sql.DB) *BookStoreDB {
	return &BookStoreDB{db: db}
}

func (s *BookStoreDB) Create(req *models.BookRequest) (*models.Book, error) {
	if req.Title == "" || req.Author == "" {
		return nil, errors.New("title and author are required")
	}

	id := uuid.New().String()
	now := time.Now()

	query := `
		INSERT INTO books (id, title, author, year, isbn, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`
	_, err := s.db.Exec(query, id, req.Title, req.Author, req.Year, req.ISBN, now, now)
	if err != nil {
		return nil, fmt.Errorf("failed to create book: %w", err)
	}

	book := &models.Book{
		ID:        id,
		Title:     req.Title,
		Author:    req.Author,
		Year:      req.Year,
		ISBN:      req.ISBN,
		CreatedAt: now,
		UpdatedAt: now,
	}

	log.Printf("Created book with ID: %s", id)
	return book, nil
}

func (s *BookStoreDB) GetByID(id string) (*models.Book, error) {
	query := `
		SELECT id, title, author, year, isbn, created_at, updated_at
		FROM books
		WHERE id = ?
	`
	row := s.db.QueryRow(query, id)

	var book models.Book
	err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, errors.New("book not found")
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}

	return &book, nil
}

func (s *BookStoreDB) List(authorFilter string) ([]models.Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = `
			SELECT id, title, author, year, isbn, created_at, updated_at
			FROM books
			WHERE author LIKE ?
			ORDER BY created_at DESC
		`
		args = append(args, "%"+authorFilter+"%")
	} else {
		query = `
			SELECT id, title, author, year, isbn, created_at, updated_at
			FROM books
			ORDER BY created_at DESC
		`
	}

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []models.Book
	for rows.Next() {
		var book models.Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN, &book.CreatedAt, &book.UpdatedAt)
		if err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, book)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return books, nil
}

func (s *BookStoreDB) Update(id string, req *models.BookRequest) (*models.Book, error) {
	if req.Title == "" || req.Author == "" {
		return nil, errors.New("title and author are required")
	}

	// Check if book exists
	existing, err := s.GetByID(id)
	if err != nil {
		return nil, err
	}

	now := time.Now()
	query := `
		UPDATE books
		SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		WHERE id = ?
	`
	_, err = s.db.Exec(query, req.Title, req.Author, req.Year, req.ISBN, now, id)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	updatedBook := &models.Book{
		ID:        id,
		Title:     req.Title,
		Author:    req.Author,
		Year:      req.Year,
		ISBN:      req.ISBN,
		CreatedAt: existing.CreatedAt,
		UpdatedAt: now,
	}

	log.Printf("Updated book with ID: %s", id)
	return updatedBook, nil
}

func (s *BookStoreDB) Delete(id string) error {
	// Check if book exists
	_, err := s.GetByID(id)
	if err != nil {
		return err
	}

	query := "DELETE FROM books WHERE id = ?"
	result, err := s.db.Exec(query, id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return errors.New("book not found")
	}

	log.Printf("Deleted book with ID: %s", id)
	return nil
}