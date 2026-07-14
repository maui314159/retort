package main

import "errors"

// Book is the canonical representation of a book stored in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate enforces the required-field contract for a book. title and author
// are mandatory; year, if provided, must be a plausible publication year.
func (b Book) validate() error {
	if b.Title == "" {
		return errors.New("title is required")
	}
	if b.Author == "" {
		return errors.New("author is required")
	}
	if b.Year != 0 && (b.Year < 0 || b.Year > 3000) {
		return errors.New("year is out of range")
	}
	return nil
}
