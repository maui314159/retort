package main

import (
	"errors"
	"strings"
)

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// Validate validates required fields and basic constraints on a Book.
// Title and Author are required and must be non-empty after trimming.
// Year, if provided, must be a positive number.
func (b *Book) Validate() error {
	if strings.TrimSpace(b.Title) == "" {
		return errors.New("title is required")
	}
	if strings.TrimSpace(b.Author) == "" {
		return errors.New("author is required")
	}
	if b.Year != 0 && b.Year < 0 {
		return errors.New("year must be a positive number")
	}
	return nil
}
