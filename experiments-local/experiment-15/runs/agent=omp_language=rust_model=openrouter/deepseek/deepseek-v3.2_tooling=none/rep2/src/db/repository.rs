use sqlx::{SqlitePool, query, query_as};
use uuid::Uuid;

use crate::models::Book;
use crate::error::AppError;

#[derive(sqlx::FromRow)]
struct BookRow {
    id: String,
    title: String,
    author: String,
    year: i64,
    isbn: String,
}

impl TryFrom<BookRow> for Book {
    type Error = AppError;

    fn try_from(row: BookRow) -> Result<Self, Self::Error> {
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
    }
}

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
        let rows: Vec<BookRow> = if let Some(author) = author_filter {
            query_as!(
                BookRow,
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
            query_as!(
                BookRow,
                r#"
                SELECT id, title, author, year, isbn
                FROM books
                ORDER BY title
                "#
            )
            .fetch_all(&self.pool)
            .await?
        };

        rows.into_iter()
            .map(|row| row.try_into())
            .collect()
    }

    pub async fn find_by_id(&self, id: Uuid) -> Result<Option<Book>, AppError> {
        let id_str = id.to_string();
        let row = query_as!(
            BookRow,
            r#"
            SELECT id, title, author, year, isbn
            FROM books
            WHERE id = $1
            "#,
            id_str
        )
        .fetch_optional(&self.pool)
        .await?;

        row.map(|r| r.try_into()).transpose()
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