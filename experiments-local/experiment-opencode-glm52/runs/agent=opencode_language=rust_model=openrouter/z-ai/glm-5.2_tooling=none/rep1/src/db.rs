use crate::error::AppResult;
use crate::models::{Book, CreateBook, UpdateBook};
use rusqlite::{params, Connection};
use std::path::Path;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct Db {
    conn: Arc<Mutex<Connection>>,
}

impl Db {
    pub fn open<P: AsRef<Path>>(path: P) -> AppResult<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id     TEXT PRIMARY KEY,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );",
        )?;
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    pub fn open_in_memory() -> AppResult<Self> {
        let conn = Connection::open_in_memory()?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id     TEXT PRIMARY KEY,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );",
        )?;
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    pub fn insert(&self, id: &str, book: &CreateBook) -> AppResult<Book> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![id, book.title, book.author, book.year, book.isbn],
        )?;
        drop(conn);
        self.get(id)
    }

    pub fn list(&self, author_filter: Option<&str>) -> AppResult<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let books: Vec<Book> = match author_filter {
            Some(author) => {
                let mut stmt = conn.prepare(
                    "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
                )?;
                let rows = stmt.query_map(params![author], map_book)?;
                rows.collect::<rusqlite::Result<Vec<_>>>()?
            }
            None => {
                let mut stmt =
                    conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
                let rows = stmt.query_map([], map_book)?;
                rows.collect::<rusqlite::Result<Vec<_>>>()?
            }
        };
        Ok(books)
    }

    pub fn get(&self, id: &str) -> AppResult<Book> {
        let conn = self.conn.lock().unwrap();
        let book = conn.query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            map_book,
        );
        match book {
            Ok(b) => Ok(b),
            Err(rusqlite::Error::QueryReturnedNoRows) => Err(crate::error::AppError::NotFound(
                format!("book with id '{id}' not found"),
            )),
            Err(e) => Err(e.into()),
        }
    }

    pub fn update(&self, id: &str, update: &UpdateBook) -> AppResult<Book> {
        {
            let conn = self.conn.lock().unwrap();
            let exists = conn.query_row(
                "SELECT 1 FROM books WHERE id = ?1",
                params![id],
                |_| Ok(()),
            );
            match exists {
                Ok(_) => {}
                Err(rusqlite::Error::QueryReturnedNoRows) => {
                    return Err(crate::error::AppError::NotFound(format!(
                        "book with id '{id}' not found"
                    )))
                }
                Err(e) => return Err(e.into()),
            }
            conn.execute(
                "UPDATE books SET
                    title  = COALESCE(?1, title),
                    author = COALESCE(?2, author),
                    year   = COALESCE(?3, year),
                    isbn   = COALESCE(?4, isbn)
                 WHERE id = ?5",
                params![update.title, update.author, update.year, update.isbn, id],
            )?;
        }
        self.get(id)
    }

    pub fn delete(&self, id: &str) -> AppResult<()> {
        let conn = self.conn.lock().unwrap();
        let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        if affected == 0 {
            Err(crate::error::AppError::NotFound(format!(
                "book with id '{id}' not found"
            )))
        } else {
            Ok(())
        }
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
