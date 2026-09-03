package main

import "encoding/json"

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// bookInput is used to validate create/update payloads.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// validate checks required fields. requireAll controls whether all
// fields must be present (for full PUT updates) or only some (POST).
func (b *bookInput) validate(requireAll bool) []string {
	var errs []string
	if b.Title == nil {
		if requireAll {
			errs = append(errs, "title is required")
		}
	} else if *b.Title == "" {
		errs = append(errs, "title must not be empty")
	}
	if b.Author == nil {
		if requireAll {
			errs = append(errs, "author is required")
		}
	} else if *b.Author == "" {
		errs = append(errs, "author must not be empty")
	}
	if b.Year != nil && *b.Year < 0 {
		errs = append(errs, "year must be a positive integer")
	}
	return errs
}

// decodeBookInput parses and returns a bookInput from the request body.
func decodeBookInput(body []byte) (*bookInput, error) {
	var in bookInput
	if err := json.Unmarshal(body, &in); err != nil {
		return nil, err
	}
	return &in, nil
}
