package main

import "time"

// Book represents a single entry in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      *int      `json:"year,omitempty"`
	ISBN      string    `json:"isbn,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// bookInput is the request payload used for create and update operations.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year,omitempty"`
	ISBN   *string `json:"isbn,omitempty"`
}

// validate ensures required fields are present and non-empty. Use this for
// create operations where every required field must be supplied.
func (in bookInput) validate() map[string]string {
	errs := in.validatePartial()
	if in.Title == nil || empty(*in.Title) {
		errs["title"] = "title is required"
	}
	if in.Author == nil || empty(*in.Author) {
		errs["author"] = "author is required"
	}
	return errs
}

// validatePartial validates only the fields that are present. Use this for
// update operations where omitted fields keep their existing values.
func (in bookInput) validatePartial() map[string]string {
	errs := map[string]string{}
	if in.Title != nil && empty(*in.Title) {
		errs["title"] = "title must not be empty"
	}
	if in.Author != nil && empty(*in.Author) {
		errs["author"] = "author must not be empty"
	}
	if in.Year != nil && (*in.Year < 0 || *in.Year > 9999) {
		errs["year"] = "year must be between 0 and 9999"
	}
	if in.ISBN != nil && len(*in.ISBN) > 32 {
		errs["isbn"] = "isbn must be at most 32 characters"
	}
	return errs
}

func empty(s string) bool {
	for _, r := range s {
		if r != ' ' && r != '\t' && r != '\n' && r != '\r' {
			return false
		}
	}
	return true
}
