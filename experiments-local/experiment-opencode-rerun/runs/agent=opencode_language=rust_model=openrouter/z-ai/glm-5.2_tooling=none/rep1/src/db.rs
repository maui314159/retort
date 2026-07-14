use std::sync::Arc;

use rusqlite::{params, Connection, OptionalExtension};

use crate::error::{AppError, AppResult};
use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Clone)]
pub struct Db {
    conn: Arc<std::sync::Mutex<Connection>>,
}

impl Db {
    pub fn open(path: &str) -> AppResult<Self> {
        let conn = Connection::open(path)?;
        Self::init(&conn)?;
        Ok(Self {
            conn: Arc::new(std::sync::Mutex::new(conn)),
        })
    }

    pub fn open_in_memory() -> AppResult<Self> {
        let conn = Connection::open_in_memory()?;
        Self::init(&conn)?;
        Ok(Self {
            conn: Arc::new(std::sync::Mutex::new(conn)),
        })
    }

    fn init(conn: &Connection) -> AppResult<()> {
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )",
            [],
        )?;
        Ok(())
    }

    pub fn create(&self, input: &CreateBook) -> AppResult<Book> {
        let conn = self.conn.lock().expect("db mutex poisoned");
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            params![&input.title, &input.author, input.year, input.isbn],
        )?;
        let id = conn.last_insert_rowid();
        Ok(Book {
            id,
            title: input.title.clone(),
            author: input.author.clone(),
            year: input.year,
            isbn: input.isbn.clone(),
        })
    }

    pub fn list(&self, author_filter: Option<&str>) -> AppResult<Vec<Book>> {
        let conn = self.conn.lock().expect("db mutex poisoned");
        let mut books = Vec::new();
        let stmt = if let Some(author) = author_filter {
            let mut s = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = s.query_map(params![author], map_book)?;
            for row in rows {
                books.push(row?);
            }
            s
        } else {
            let mut s = conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = s.query_map([], map_book)?;
            for row in rows {
                books.push(row?);
            }
            s
        };
        let _ = stmt.finalize();
        Ok(books)
    }
    pub fn get(&self, id: i64) -> AppResult<Book> {
        let conn = self.conn.lock().expect("db mutex poisoned");
        let book = conn
            .query_row(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
                params![id],
                map_book,
            )
            .optional()?;
        book.ok_or(AppError::NotFound)
    }

    pub fn update(&self, id: i64, input: &UpdateBook) -> AppResult<Book> {
        let existing = self.get(id)?;
        let title = input.title.clone().unwrap_or(existing.title);
        let author = input.author.clone().unwrap_or(existing.author);
        let year = input.year.or(existing.year);
        let isbn = input.isbn.clone().or(existing.isbn);

        let conn = self.conn.lock().expect("db mutex poisoned");
        let affected = conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, year, isbn, id],
        )?;
        if affected == 0 {
            return Err(AppError::NotFound);
        }
        Ok(Book {
            id,
            title,
            author,
            year,
            isbn,
        })
    }

    pub fn delete(&self, id: i64) -> AppResult<()> {
        let conn = self.conn.lock().expect("db mutex poisoned");
        let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        if affected == 0 {
            return Err(AppError::NotFound);
        }
        Ok(())
    }
}

fn map_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
