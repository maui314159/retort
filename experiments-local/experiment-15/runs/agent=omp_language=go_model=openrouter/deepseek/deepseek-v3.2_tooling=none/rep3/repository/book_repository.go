package repository

import (
	"bookapi/models"
)

type BookRepository interface {
	Create(book *models.Book) (int64, error)
	GetAll(authorFilter string) ([]models.Book, error)
	GetByID(id int) (*models.Book, error)
	Update(id int, book *models.Book) error
	Delete(id int) error
}