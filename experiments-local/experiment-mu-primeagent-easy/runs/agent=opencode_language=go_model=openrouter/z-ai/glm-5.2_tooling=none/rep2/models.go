package main

import "fmt"

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks that required fields are present.
func (b *Book) Validate() error {
	if b.Title == "" {
		return fmt.Errorf("title is required")
	}
	if b.Author == "" {
		return fmt.Errorf("author is required")
	}
	if b.Year < 0 {
		return fmt.Errorf("year must be non-negative")
	}
	return nil
}
