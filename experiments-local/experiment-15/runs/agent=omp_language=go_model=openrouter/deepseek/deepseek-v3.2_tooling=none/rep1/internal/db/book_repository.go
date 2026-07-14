package db

import (
	"database/sql"

	"bookapi/internal/models"
)

func GetAllBooks(authorFilter string) ([]models.Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = DB.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+authorFilter+"%")
	} else {
		rows, err = DB.Query("SELECT id, title, author, year, isbn FROM books")
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []models.Book
	for rows.Next() {
		var book models.Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

func GetBookByID(id int) (*models.Book, error) {
	var book models.Book
	err := DB.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return &book, nil
}

func CreateBook(book *models.Book) error {
	result, err := DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return err
	}
	book.ID = int(id)
	return nil
}

func UpdateBook(id int, book *models.Book) error {
	result, err := DB.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rowsAffected == 0 {
		return sql.ErrNoRows
	}

	return nil
}

func DeleteBook(id int) error {
	result, err := DB.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rowsAffected == 0 {
		return sql.ErrNoRows
	}

	return nil
}