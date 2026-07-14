package main

import "time"

// Book represents a single entry in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// bookInput is the request body for create/update operations. Pointers are
// not used because every field is a value type that may legitimately be the
// zero value (e.g. year 0, empty ISBN) except for the required fields.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   int     `json:"year"`
	ISBN   string  `json:"isbn"`
}

// validate enforces the required-field constraints and returns a human-readable
// error message when invalid. Required fields use pointers so we can distinguish
// "field omitted" from "field set to empty string".
func (b *bookInput) validate() string {
	if b.Title == nil || trim(*b.Title) == "" {
		return "title is required"
	}
	if b.Author == nil || trim(*b.Author) == "" {
		return "author is required"
	}
	return ""
}
