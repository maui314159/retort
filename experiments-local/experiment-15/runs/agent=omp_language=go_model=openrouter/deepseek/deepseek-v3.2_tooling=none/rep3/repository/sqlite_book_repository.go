package repository

import (
	"bookapi/models"
	"database/sql"
)

type SQLiteBookRepository struct {
	db *sql.DB
}

func NewSQLiteBookRepository(db *sql.DB) *SQLiteBookRepository {
	return &SQLiteBookRepository{db: db}
}

func (r *SQLiteBookRepository) Create(book *models.Book) (int64, error) {
	result, err := r.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		return 0, err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return 0, err
	}
	book.ID = int(id)
	return id, nil
}

func (r *SQLiteBookRepository) GetAll(authorFilter string) ([]models.Book, error) {
	var rows *sql.Rows
	var err error
	if authorFilter != "" {
		rows, err = r.db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", authorFilter)
	} else {
		rows, err = r.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []models.Book
	for rows.Next() {
		var b models.Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, nil
}

func (r *SQLiteBookRepository) GetByID(id int) (*models.Book, error) {
	var b models.Book
	err := r.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &b, nil
}

func (r *SQLiteBookRepository) Update(id int, book *models.Book) error {
	result, err := r.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, id,
	)
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

func (r *SQLiteBookRepository) Delete(id int) error {
	result, err := r.db.Exec("DELETE FROM books WHERE id = ?", id)
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