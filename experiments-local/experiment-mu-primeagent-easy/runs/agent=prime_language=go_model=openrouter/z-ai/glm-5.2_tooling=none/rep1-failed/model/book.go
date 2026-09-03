package model

// Book represents a single book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the payload used when creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate checks that required fields are present. It returns a slice of
// human-readable error messages for every invalid field.
func (b BookInput) Validate() []string {
	var errs []string
	if b.Title == "" {
		errs = append(errs, "title is required")
	}
	if b.Author == "" {
		errs = append(errs, "author is required")
	}
	if b.Year < 0 {
		errs = append(errs, "year must be a non-negative integer")
	}
	return errs
}
