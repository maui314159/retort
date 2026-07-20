//! SQLite persistence layer for the book collection.

use rusqlite::{params, Connection, OptionalExtension};

use crate::models::{Book, BookInput};

/// Create the schema if it does not exist yet.
pub fn init(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

/// Insert a new book and return it with its assigned id.
pub fn create_book(conn: &Connection, input: &BookInput) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    Ok(Book {
        id: conn.last_insert_rowid(),
        title: input.title.clone(),
        author: input.author.clone(),
        year: input.year,
        isbn: input.isbn.clone(),
    })
}

/// List all books, optionally filtered by exact author name.
pub fn list_books(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut books = Vec::new();
    match author {
        Some(author) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            for row in stmt.query_map(params![author], row_to_book)? {
                books.push(row?);
            }
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            for row in stmt.query_map([], row_to_book)? {
                books.push(row?);
            }
        }
    }
    Ok(books)
}

/// Fetch a single book by id.
pub fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

/// Replace all fields of an existing book. Returns `None` if the id is unknown.
pub fn update_book(
    conn: &Connection,
    id: i64,
    input: &BookInput,
) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
        params![id, input.title, input.author, input.year, input.isbn],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    Ok(Some(Book {
        id,
        title: input.title.clone(),
        author: input.author.clone(),
        year: input.year,
        isbn: input.isbn.clone(),
    }))
}

/// Delete a book. Returns `true` if a row was removed.
pub fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    Ok(conn.execute("DELETE FROM books WHERE id = ?1", params![id])? > 0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn conn() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        init(&conn).unwrap();
        conn
    }

    fn input(title: &str, author: &str) -> BookInput {
        BookInput {
            title: title.to_string(),
            author: author.to_string(),
            year: Some(2000),
            isbn: None,
        }
    }

    #[test]
    fn create_then_get_roundtrip() {
        let conn = conn();
        let book = create_book(&conn, &input("Dune", "Frank Herbert")).unwrap();
        assert!(book.id > 0);
        let fetched = get_book(&conn, book.id).unwrap().unwrap();
        assert_eq!(fetched.title, "Dune");
        assert_eq!(fetched.author, "Frank Herbert");
    }

    #[test]
    fn list_filters_by_author() {
        let conn = conn();
        create_book(&conn, &input("Dune", "Frank Herbert")).unwrap();
        create_book(&conn, &input("Dune Messiah", "Frank Herbert")).unwrap();
        create_book(&conn, &input("Neuromancer", "William Gibson")).unwrap();

        assert_eq!(list_books(&conn, None).unwrap().len(), 3);
        let herberts = list_books(&conn, Some("Frank Herbert")).unwrap();
        assert_eq!(herberts.len(), 2);
        assert!(herberts.iter().all(|b| b.author == "Frank Herbert"));
    }

    #[test]
    fn update_and_delete() {
        let conn = conn();
        let book = create_book(&conn, &input("Old Title", "Some Author")).unwrap();

        let updated = update_book(&conn, book.id, &input("New Title", "Some Author"))
            .unwrap()
            .unwrap();
        assert_eq!(updated.title, "New Title");
        assert!(update_book(&conn, 999, &input("X", "Y")).unwrap().is_none());

        assert!(delete_book(&conn, book.id).unwrap());
        assert!(!delete_book(&conn, book.id).unwrap());
        assert!(get_book(&conn, book.id).unwrap().is_none());
    }
}
