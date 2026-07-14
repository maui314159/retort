package db

import (
	"database/sql"
	"os"
	"testing"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	
	// Use a temporary database file
	dbPath := "test_books.db"
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		t.Fatalf("Failed to open test database: %v", err)
	}

	// Create table
	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);
	`
	_, err = db.Exec(createTable)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	// Clean up after test
	t.Cleanup(func() {
		db.Close()
		os.Remove(dbPath)
	})

	return db
}