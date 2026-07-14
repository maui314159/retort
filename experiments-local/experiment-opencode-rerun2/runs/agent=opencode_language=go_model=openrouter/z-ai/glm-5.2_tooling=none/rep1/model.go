package main

import "time"

// Book represents a book record in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year,omitempty"`
	ISBN      string    `json:"isbn,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// bookInput is used to validate and decode incoming create/update requests.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// validate checks that required fields are present and non-empty. It returns a
// slice of human-readable error messages for any validation failures.
func (b *bookInput) validate() []string {
	var errs []string
	if b.Title == nil || trimSpaces(*b.Title) == "" {
		errs = append(errs, "title is required")
	}
	if b.Author == nil || trimSpaces(*b.Author) == "" {
		errs = append(errs, "author is required")
	}
	if b.Year != nil && *b.Year < 0 {
		errs = append(errs, "year must be a non-negative integer")
	}
	return errs
}

func trimSpaces(s string) string {
	start := 0
	for start < len(s) && (s[start] == ' ' || s[start] == '\t' || s[start] == '\n' || s[start] == '\r') {
		start++
	}
	end := len(s)
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t' || s[end-1] == '\n' || s[end-1] == '\r') {
		end--
	}
	return s[start:end]
}
