// Package book defines the Book domain type used by the API and store layers.
package book

import (
	"errors"
	"fmt"
	"strings"
)

// Book is the canonical representation of a book in the collection.
//
// The JSON tags are the wire format. The store layer maps these columns to a
// SQLite row; the API layer maps these to JSON responses.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input is the subset of Book fields a client may supply on create/update.
// ID is assigned by the store and never accepted from the wire.
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrValidation is returned for caller-fixable input problems. The API layer
// translates it into HTTP 400. The wrapped message is human-readable on a
// single line — no embedded newlines, so it can be rendered in a JSON
// {"error": "..."} payload without surprising clients.
var ErrValidation = errors.New("validation failed")

// Validate enforces the API contract: title and author are required (after
// trimming whitespace); year must be non-negative if supplied. ISBN is
// optional. Returns ErrValidation wrapping a descriptive message.
func (in Input) Validate() error {
	title := strings.TrimSpace(in.Title)
	author := strings.TrimSpace(in.Author)
	switch {
	case title == "":
		return joinErr("title is required")
	case author == "":
		return joinErr("author is required")
	case in.Year < 0:
		return joinErr("year must be non-negative")
	}
	return nil
}

// Normalize returns a copy of the input with surrounding whitespace stripped
// from the string fields. Callers should use the result when persisting.
func (in Input) Normalize() Input {
	return Input{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}
}

func joinErr(msg string) error {
	// Use a single-line wrapped error so the API's JSON error field renders
	// cleanly. errors.Join would otherwise embed a newline between the
	// sentinel and the cause, leaking Go's default error formatting.
	return fmt.Errorf("%w: %s", ErrValidation, msg)
}
