package main


type Book struct {
	ID        int64  `json:"id"`
	Title     string `json:"title"`
	Author    string `json:"author"`
	Year      *int   `json:"year,omitempty"`
	ISBN      string `json:"isbn,omitempty"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}
