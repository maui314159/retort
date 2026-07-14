package main

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

func (b Book) Validate() string {
	if b.Title == "" {
		return "title is required"
	}
	if b.Author == "" {
		return "author is required"
	}
	if b.Year < 0 {
		return "year must be a non-negative integer"
	}
	return ""
}
