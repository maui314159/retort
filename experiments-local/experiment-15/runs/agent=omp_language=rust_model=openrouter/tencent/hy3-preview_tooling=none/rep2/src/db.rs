use crate::models::Book;
use chrono::{DateTime, Utc};
use sqlx::{sqlite::SqlitePool, Error as SqlxError, Row};
use uuid::Uuid;

pub struct Database {
    pool: SqlitePool,
}

impl Database {
    pub async fn new(database_url: &str) -> Result<Self, SqlxError> {
        let pool = SqlitePool::connect(database_url).await?;
        Ok(Database { pool })
    }

    pub async fn migrate(&self) -> Result<(), SqlxError> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            "#,
        )
        .execute(&self.pool)
        .await?;
        Ok(())
    }

    fn parse_datetime(s: &str) -> Result<DateTime<Utc>, chrono::ParseError> {
        Ok(DateTime::parse_from_rfc3339(s)?.with_timezone(&Utc))
    }

    fn row_to_book(&self, row: sqlx::sqlite::SqliteRow) -> Result<Book, SqlxError> {
        let id: String = row.try_get("id")?;
        let title: String = row.try_get("title")?;
        let author: String = row.try_get("author")?;
        let year: Option<i32> = row.try_get("year")?;
        let isbn: Option<String> = row.try_get("isbn")?;
        let created_at_str: String = row.try_get("created_at")?;
        let updated_at_str: String = row.try_get("updated_at")?;

        let created_at = Self::parse_datetime(&created_at_str)
            .map_err(|e| SqlxError::ColumnDecode {
                index: "created_at".into(),
                source: Box::new(e),
            })?;
        let updated_at = Self::parse_datetime(&updated_at_str)
            .map_err(|e| SqlxError::ColumnDecode {
                index: "updated_at".into(),
                source: Box::new(e),
            })?;

        Ok(Book {
            id,
            title,
            author,
            year,
            isbn,
            created_at,
            updated_at,
        })
    }

    pub async fn create_book(
        &self,
        title: &str,
        author: &str,
        year: Option<i32>,
        isbn: Option<&str>,
    ) -> Result<Book, SqlxError> {
        let id = Uuid::new_v4().to_string();
        let now = Utc::now();

        sqlx::query(
            r#"
            INSERT INTO books (id, title, author, year, isbn, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(&id)
        .bind(title)
        .bind(author)
        .bind(year)
        .bind(isbn)
        .bind(now.to_rfc3339())
        .bind(now.to_rfc3339())
        .execute(&self.pool)
        .await?;

        self.get_book(&id).await
    }

    pub async fn get_book(&self, id: &str) -> Result<Book, SqlxError> {
        let row = sqlx::query(
            r#"
            SELECT id, title, author, year, isbn, created_at, updated_at
            FROM books
            WHERE id = ?
            "#,
        )
        .bind(id)
        .fetch_one(&self.pool)
        .await?;

        self.row_to_book(row)
    }

    pub async fn list_books(&self, author_filter: Option<&str>) -> Result<Vec<Book>, SqlxError> {
        let rows = if let Some(author) = author_filter {
            sqlx::query(
                r#"
                SELECT id, title, author, year, isbn, created_at, updated_at
                FROM books
                WHERE author LIKE ?
                ORDER BY created_at DESC
                "#,
            )
            .bind(format!("%{}%", author))
            .fetch_all(&self.pool)
            .await?
        } else {
            sqlx::query(
                r#"
                SELECT id, title, author, year, isbn, created_at, updated_at
                FROM books
                ORDER BY created_at DESC
                "#,
            )
            .fetch_all(&self.pool)
            .await?
        };

        rows.into_iter()
            .map(|row| self.row_to_book(row))
            .collect::<Result<Vec<_>, _>>()
    }

    pub async fn update_book(
        &self,
        id: &str,
        title: Option<&str>,
        author: Option<&str>,
        year: Option<i32>,
        isbn: Option<&str>,
    ) -> Result<Book, SqlxError> {
        let existing = self.get_book(id).await?;
        let now = Utc::now();

        let new_title = title.unwrap_or(&existing.title);
        let new_author = author.unwrap_or(&existing.author);
        let new_year = year.or(existing.year);
        let new_isbn = isbn.or(existing.isbn.as_deref());

        sqlx::query(
            r#"
            UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
            WHERE id = ?
            "#,
        )
        .bind(new_title)
        .bind(new_author)
        .bind(new_year)
        .bind(new_isbn)
        .bind(now.to_rfc3339())
        .bind(id)
        .execute(&self.pool)
        .await?;

        self.get_book(id).await
    }

    pub async fn delete_book(&self, id: &str) -> Result<(), SqlxError> {
        sqlx::query("DELETE FROM books WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await?;
        Ok(())
    }
}
