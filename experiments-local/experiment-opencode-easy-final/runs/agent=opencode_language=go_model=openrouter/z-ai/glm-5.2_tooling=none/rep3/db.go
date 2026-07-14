package main

import (
	"database/sql"
	"time"

	_ "modernc.org/sqlite"
)

// Store wraps the database connection and provides data access methods.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures the
// schema is in place.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // SQLite handles single writer best.
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	s := &Store{db: db}
	if err := s.initSchema(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

func (s *Store) initSchema() error {
	const q = `
CREATE TABLE IF NOT EXISTS books (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  title      TEXT NOT NULL,
  author     TEXT NOT NULL,
  year       INTEGER,
  isbn       TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
`
	_, err := s.db.Exec(q)
	return err
}

// Create inserts a new book and returns the populated record.
func (s *Store) Create(b Book) (Book, error) {
	now := time.Now().UTC()
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, nullableInt(b.Year), b.ISBN, now, now,
	)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	return s.Get(id)
}

// List returns every book, optionally filtered by author (case-insensitive
// exact match).
func (s *Store) List(author string) ([]Book, error) {
	rows, err := s.db.Query(`
	    SELECT id, title, author, year, isbn, created_at, updated_at
	      FROM books
	     WHERE (? = '' OR LOWER(author) = LOWER(?))
	  ORDER BY id ASC`, author, author)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Book
	for rows.Next() {
		var b Book
		var year sql.NullInt64
		var isbn sql.NullString
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, err
		}
		if year.Valid {
			y := int(year.Int64)
			b.Year = &y
		}
		if isbn.Valid {
			b.ISBN = isbn.String
		}
		out = append(out, b)
	}
	return out, rows.Err()
}

// Get returns a single book by id. Returns sql.ErrNoRows when not found.
func (s *Store) Get(id int64) (Book, error) {
	var b Book
	var year sql.NullInt64
	var isbn sql.NullString
	err := s.db.QueryRow(`
	SELECT id, title, author, year, isbn, created_at, updated_at
	  FROM books
	 WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	if isbn.Valid {
		b.ISBN = isbn.String
	}
	return b, nil
}

// Update merges non-nil fields of in into the row identified by id.
func (s *Store) Update(id int64, in bookInput) (Book, error) {
	cur, err := s.Get(id)
	if err != nil {
		return Book{}, err
	}
	if in.Title != nil {
		cur.Title = *in.Title
	}
	if in.Author != nil {
		cur.Author = *in.Author
	}
	if in.Year != nil {
		cur.Year = in.Year
	}
	if in.ISBN != nil {
		cur.ISBN = *in.ISBN
	}
	_, err = s.db.Exec(`
		UPDATE books
		   SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
	     WHERE id = ?`,
		cur.Title, cur.Author, nullableInt(cur.Year), cur.ISBN, time.Now().UTC(), id)
	if err != nil {
		return Book{}, err
	}
	return s.Get(id)
}

// Delete removes the row identified by id. It is a no-op if the row does not
// exist.
func (s *Store) Delete(id int64) error {
	_, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	return err
}

func nullableInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}
