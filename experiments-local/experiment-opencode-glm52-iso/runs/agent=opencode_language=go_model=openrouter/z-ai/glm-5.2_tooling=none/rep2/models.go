package main

import "time"

// Book represents a book record in the collection.
type Book struct {
	ID        int64  `json:"id"`
	Title     string `json:"title"`
	Author    string `json:"author"`
	Year      int    `json:"year"`
	ISBN      string `json:"isbn"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// bookInput is used for validating create/update payloads.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// validate checks required fields and returns an error message when invalid.
func (b *bookInput) validate() string {
	if b.Title == nil || trimSpaces(*b.Title) == "" {
		return "title is required"
	}
	if b.Author == nil || trimSpaces(*b.Author) == "" {
		return "author is required"
	}
	if b.Year != nil && *b.Year < 0 {
		return "year must be a non-negative integer"
	}
	if b.Year != nil && *b.Year > time.Now().Year()+1 {
		return "year is out of range"
	}
	return ""
}

func trimSpaces(s string) string {
	start, end := 0, len(s)
	for start < end && (s[start] == ' ' || s[start] == '\t' || s[start] == '\n' || s[start] == '\r') {
		start++
	}
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t' || s[end-1] == '\n' || s[end-1] == '\r') {
		end--
	}
	return s[start:end]
}
