package main

// Book represents a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// bookRequest is the payload for creating or updating a book.
type bookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// validate checks that required fields are present and returns a
// human-readable error message, or an empty string when valid.
func (b *bookRequest) validate() string {
	if b.Title == "" {
		return "title is required"
	}
	if b.Author == "" {
		return "author is required"
	}
	return ""
}
