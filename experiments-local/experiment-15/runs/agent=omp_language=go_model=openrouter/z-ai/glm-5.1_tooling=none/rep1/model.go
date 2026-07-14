package main

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

func (b BookInput) Validate() map[string]string {
	errs := make(map[string]string)
	if b.Title == "" {
		errs["title"] = "title is required"
	}
	if b.Author == "" {
		errs["author"] = "author is required"
	}
	return errs
}
