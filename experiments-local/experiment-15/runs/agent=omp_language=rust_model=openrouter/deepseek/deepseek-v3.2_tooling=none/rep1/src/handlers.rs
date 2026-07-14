use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde::Deserialize;
use sqlx::SqlitePool;

use crate::{
    error::AppError,
    models::{Book, CreateBook, UpdateBook},
};

#[derive(Deserialize)]
pub struct ListBooksQuery {
    pub author: Option<String>,
}

pub async fn health() -> &'static str {
    "OK"
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    payload.validate()?;

    let book = Book::new(payload);
    book.validate()?;

    let result = sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(&book.id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&pool)
    .await;

    match result {
        Ok(_) => Ok((StatusCode::CREATED, Json(book))),
        Err(sqlx::Error::Database(db_err)) if db_err.message().contains("UNIQUE constraint failed") => {
            Err(AppError::DuplicateIsbn)
        }
        Err(e) => Err(AppError::Database(e)),
    }
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(query): Query<ListBooksQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = if let Some(author) = query.author {
        sqlx::query_as::<_, Book>("SELECT * FROM books WHERE author = ? ORDER BY title")
            .bind(author)
            .fetch_all(&pool)
            .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT * FROM books ORDER BY title")
            .fetch_all(&pool)
            .await?
    };

    Ok(Json(books))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<Json<Book>, AppError> {
    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await?;

    match book {
        Some(book) => Ok(Json(book)),
        None => Err(AppError::NotFound),
    }
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let existing_book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(&id)
        .fetch_optional(&pool)
        .await?;

    if existing_book.is_none() {
        return Err(AppError::NotFound);
    }

    let title = payload.title.as_deref();
    let author = payload.author.as_deref();
    let year = payload.year;
    let isbn = payload.isbn.as_deref();

    if let Some(isbn) = isbn {
        let existing = sqlx::query_scalar::<_, String>(
            "SELECT id FROM books WHERE isbn = ? AND id != ? LIMIT 1",
        )
        .bind(isbn)
        .bind(&id)
        .fetch_optional(&pool)
        .await?;

        if existing.is_some() {
            return Err(AppError::DuplicateIsbn);
        }
    }

    let mut updates = Vec::new();
    let mut params: Vec<String> = Vec::new();

    if let Some(title) = title {
        updates.push("title = ?");
        params.push(title.to_string());
    }
    if let Some(author) = author {
        updates.push("author = ?");
        params.push(author.to_string());
    }
    if let Some(year) = year {
        updates.push("year = ?");
        params.push(year.to_string());
    }
    if let Some(isbn) = isbn {
        updates.push("isbn = ?");
        params.push(isbn.to_string());
    }

    if updates.is_empty() {
        return get_book(State(pool), Path(id)).await;
    }

    updates.push("updated_at = CURRENT_TIMESTAMP");

    let query_str = format!("UPDATE books SET {} WHERE id = ?", updates.join(", "));
    let mut query = sqlx::query(&query_str);

    for param in &params {
        query = query.bind(param);
    }
    query = query.bind(&id);

    query.execute(&pool).await?;

    get_book(State(pool), Path(id)).await
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<StatusCode, AppError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await?;

    if result.rows_affected() == 0 {
        Err(AppError::NotFound)
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

pub fn create_router(pool: sqlx::SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .with_state(pool)
}