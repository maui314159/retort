package main

import (
	"errors"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var (
	ErrTitleRequired  = errors.New("title is required")
	ErrAuthorRequired = errors.New("author is required")
)

func (b *Book) Validate() error {
	if b.Title == "" {
		return ErrTitleRequired
	}
	if b.Author == "" {
		return ErrAuthorRequired
	}
	return nil
}
