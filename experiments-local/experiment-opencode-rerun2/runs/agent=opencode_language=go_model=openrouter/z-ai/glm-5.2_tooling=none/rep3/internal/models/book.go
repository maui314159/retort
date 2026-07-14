package models

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// BookInput is the payload accepted on create/update endpoints.
// Title and Author are required; Year and ISBN are optional.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// Validate checks that required fields are present.
func (b BookInput) Validate() error {
	if b.Title == "" {
		return ValidationError{Field: "title", Message: "title is required"}
	}
	if b.Author == "" {
		return ValidationError{Field: "author", Message: "author is required"}
	}
	if b.Year < 0 {
		return ValidationError{Field: "year", Message: "year must be non-negative"}
	}
	return nil
}

type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

func (e ValidationError) Error() string { return e.Message }
