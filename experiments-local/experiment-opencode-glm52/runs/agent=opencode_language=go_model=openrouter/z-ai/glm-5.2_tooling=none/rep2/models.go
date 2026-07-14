package main

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// bookInput is the request body shape for create/update operations.
type bookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// validate checks required fields. For PUT operations all fields are
// replaced, so empties are rejected. errFields holds the list of missing
// field names, if any.
func (b *bookInput) validate() []string {
	var missing []string
	if b.Title == nil || *b.Title == "" {
		missing = append(missing, "title")
	}
	if b.Author == nil || *b.Author == "" {
		missing = append(missing, "author")
	}
	return missing
}
