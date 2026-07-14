use sqlx::{SqlitePool, query, query_as};
use uuid::Uuid;

use crate::models::Book;
use crate::error::AppError;

#[derive(Clone)]
pub struct BookRepository {
    pool: SqlitePool,
}

impl BookRepository {
    pub fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }

    pub async fn create(&self, book: &Book) -> Result<Book, AppError> {
        let id_str = book.id.to_string();
        query!(
            r#"
            INSERT INTO books (id, title, author, year, isbn)
            VALUES ($1, $2, $3, $4, $5)
            "#,
            id_str,
            book.title,
            book.author,
            book.year,
            book.isbn
        )
        .execute(&self.pool)
        .await?;

        Ok(book.clone())
    }

    pub async fn find_all(&self, author_filter: Option<String>) -> Result<Vec<Book>, AppError> {
        let rows = if let Some(author) = author_filter {
            query!(
                r#"
                SELECT id, title, author, year, isbn
                FROM books
                WHERE author = $1
                ORDER BY title
                "#,
                author
            )
            .fetch_all(&self.pool)
            .await?
        } else {
            query!(
                r#"
                SELECT id, title, author, year, isbn
                FROM books
                ORDER BY title
                "#
            )
            .fetch_all(&self.pool)
            .await?
        };

        let books = rows
            .into_iter()
            .map(|row| {
                let id = Uuid::parse_str(&row.id).map_err(|e| {
                    AppError::Database(sqlx::Error::Decode(Box::new(e)))
                })?;
                Ok(Book {
                    id,
                    title: row.title,
                    author: row.author,
                    year: row.year,
                    isbn: row.isbn,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;

        Ok(books)
    }

    pub async fn find_by_id(&self, id: Uuid) -> Result<Option<Book>, AppError> {
        let id_str = id.to_string();
        let row = query!(
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            WHERE id = $1
            "#,
            id_str
        )
        .fetch_optional(&self.pool)
        .await?;

        match row {
            Some(row) => {
                let id = Uuid::parse_str(&row.id).map_err(|e| {
                    AppError::Database(sqlx::Error::Decode(Box::new(e)))
                })?;
                Ok(Some(Book {
                    id,
                    title: row.title,
                    author: row.author,
                    year: row.year,
                    isbn: row.isbn,
                }))
            }
            None => Ok(None),
        }
    }

    pub async fn update(&self, id: Uuid, book: &Book) -> Result<Book, AppError> {
        let id_str = id.to_string();
        let affected = query!(
            r#"
            UPDATE books
            SET title = $2, author = $3, year = $4, isbn = $5
            WHERE id = $1
            "#,
            id_str,
            book.title,
            book.author,
            book.year,
            book.isbn
        )
        .execute(&self.pool)
        .await?;

        if affected.rows_affected() == 0 {
            return Err(AppError::NotFound);
        }

        Ok(book.clone())
    }

    pub async fn delete(&self, id: Uuid) -> Result<bool, AppError> {
        let id_str = id.to_string();
        let result = query!(
            r#"
            DELETE FROM books
            WHERE id = $1
            "#,
            id_str
        )
        .execute(&self.pool)
        .await?;

        Ok(result.rows_affected() > 0)
    }
}