package main

import (
	"errors"
	"fmt"
	"net/http"
)

// Book represents a book record in the collection.
type Book struct {
	ID    int64  `json:"id"`
	Title string `json:"title"`
	Author string `json:"author"`
	Year  *int   `json:"year,omitempty"`
	ISBN  string `json:"isbn,omitempty"`
}

// BookInput is the payload for creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// Validate checks that required fields are present and that optional
// fields satisfy their constraints. It returns a descriptive error
// together with an appropriate HTTP status code.
func (b BookInput) Validate() (int, error) {
	if b.Title == "" {
		return http.StatusBadRequest, errors.New("title is required")
	}
	if b.Author == "" {
		return http.StatusBadRequest, errors.New("author is required")
	}
	if b.Year != nil {
		if *b.Year < 0 || *b.Year > 9999 {
			return http.StatusBadRequest, fmt.Errorf("year must be between 0 and 9999")
		}
	}
	return 0, nil
}
