use sqlx::SqlitePool;
use uuid::Uuid;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub async fn init_db(database_url: &str) -> Result<SqlitePool, sqlx::Error> {
    let pool = SqlitePool::connect(database_url).await?;
    
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT
        )
        "#
    ).execute(&pool).await?;
    
    Ok(pool)
}

pub async fn create_book(pool: &SqlitePool, req: CreateBookRequest) -> Result<Book, sqlx::Error> {
    let id = Uuid::new_v4();
    let title = req.title.clone();
    let author = req.author.clone();
    let year = req.year;
    let isbn = req.isbn.clone();
    
    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
    )
    .bind(id.to_string())
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(&isbn)
    .execute(pool).await?;
    
    Ok(Book { id: id.to_string(), title, author, year, isbn })
}

pub async fn list_books(pool: &SqlitePool, author_filter: Option<String>) -> Result<Vec<Book>, sqlx::Error> {
    if let Some(author) = &author_filter {
        let pattern = format!("%{}%", author);
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?"
        )
        .bind(pattern)
        .fetch_all(pool).await
    } else {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books"
        ).fetch_all(pool).await
    }
}

pub async fn get_book(pool: &SqlitePool, id: Uuid) -> Result<Option<Book>, sqlx::Error> {
    sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
    )
    .bind(id.to_string())
    .fetch_optional(pool).await
}

pub async fn update_book(pool: &SqlitePool, id: Uuid, req: UpdateBookRequest) -> Result<Option<Book>, sqlx::Error> {
    let Some(existing) = get_book(pool, id).await? else {
        return Ok(None);
    };

    let new_title = req.title.unwrap_or(existing.title);
    let new_author = req.author.unwrap_or(existing.author);
    let new_year = req.year.unwrap_or(existing.year);
    let new_isbn = req.isbn.or(existing.isbn);

    sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    )
    .bind(&new_title)
    .bind(&new_author)
    .bind(new_year)
    .bind(&new_isbn)
    .bind(id.to_string())
    .execute(pool).await?;
    
    Ok(Some(Book {
        id: id.to_string(),
        title: new_title,
        author: new_author,
        year: new_year,
        isbn: new_isbn,
    }))
}

pub async fn delete_book(pool: &SqlitePool, id: Uuid) -> Result<bool, sqlx::Error> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id.to_string())
        .execute(pool).await?;
    Ok(result.rows_affected() > 0)
}
