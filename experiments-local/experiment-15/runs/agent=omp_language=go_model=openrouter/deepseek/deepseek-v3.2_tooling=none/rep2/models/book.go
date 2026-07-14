package models

import (
	"time"
)

type Book struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type BookRequest struct {
	Title  string `json:"title" validate:"required"`
	Author string `json:"author" validate:"required"`
	Year   int    `json:"year" validate:"min=0,max=2100"`
	ISBN   string `json:"isbn"`
}

type BookResponse struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type BookStore interface {
	Create(book *BookRequest) (*Book, error)
	GetByID(id string) (*Book, error)
	List(authorFilter string) ([]Book, error)
	Update(id string, book *BookRequest) (*Book, error)
	Delete(id string) error
}