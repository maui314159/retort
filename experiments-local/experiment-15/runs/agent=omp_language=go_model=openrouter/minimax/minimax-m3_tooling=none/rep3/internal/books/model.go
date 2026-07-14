// Package books provides storage and HTTP handlers for a book collection.
package books

import "errors"

// ErrNotFound is returned by the store when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Book represents a book in the collection.
//
// ID is assigned by the store on Create. Title and Author are required;
// Year and ISBN are optional. The same struct is used as both the wire
// format (input on POST/PUT) and the persisted representation.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Validate enforces that Title and Author are non-empty. Year and ISBN
// are optional. It returns the first problem it finds so the caller
// can surface a clear error to clients.
func (b *Book) Validate() error {
	if b.Title == "" {
		return errors.New("title is required")
	}
	if b.Author == "" {
		return errors.New("author is required")
	}
	return nil
}
