package main

// Book represents a book record returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the payload accepted on create/update.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks the required fields of a BookInput.
// Title and Author must be non-empty.
func (b BookInput) Validate() error {
	if b.Title == "" {
		return validationError{"title is required"}
	}
	if b.Author == "" {
		return validationError{"author is required"}
	}
	return nil
}

// validationError is returned when input fails validation.
type validationError struct {
	msg string
}

func (e validationError) Error() string { return e.msg }
