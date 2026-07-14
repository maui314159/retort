package main

import "time"

// Book represents a book record in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks that required fields are present and valid.
// Title and author are required; year must be reasonable.
func (b Book) Validate() error {
	if b.Title == "" {
		return ErrValidation("title is required")
	}
	if b.Author == "" {
		return ErrValidation("author is required")
	}
	if b.Year < 0 || b.Year > time.Now().Year()+1 {
		return ErrValidation("year is out of range")
	}
	return nil
}

// APIError is a structured error carrying an HTTP status code.
type APIError struct {
	Status  int    `json:"-"`
	Message string `json:"error"`
}

func (e APIError) Error() string { return e.Message }

// ErrValidation returns a 400 validation error.
func ErrValidation(msg string) APIError {
	return APIError{Status: 400, Message: msg}
}

// ErrNotFound returns a 404 error.
func ErrNotFound(msg string) APIError {
	return APIError{Status: 404, Message: msg}
}
