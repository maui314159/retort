// Package book defines the Book domain model, validation, and storage.
package book

import (
	"errors"
	"regexp"
	"time"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// ErrValidation signals invalid input. Handlers map it to HTTP 400.
var ErrValidation = errors.New("invalid book")

var isbnRe = regexp.MustCompile(`^[0-9]{10}([0-9]{3})?$`)

// Validate enforces the required-field and format rules.
// Title and Author are required and non-empty. ISBN, when provided,
// must be a 10- or 13-digit string.
func (b Book) Validate() error {
	if b.Title == "" {
		return ErrValidation
	}
	if b.Author == "" {
		return ErrValidation
	}
	if b.ISBN != "" && !isbnRe.MatchString(b.ISBN) {
		return ErrValidation
	}
	if b.Year < 0 || b.Year > time.Now().Year() {
		return ErrValidation
	}
	return nil
}
