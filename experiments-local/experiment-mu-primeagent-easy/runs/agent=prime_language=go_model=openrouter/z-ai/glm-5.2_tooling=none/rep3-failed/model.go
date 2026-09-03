package main

// Book represents a single book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// bookInput is used to decode and validate incoming JSON for
// create/update requests. Pointers distinguish "field omitted" from
// "field set to zero value" on updates.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}
