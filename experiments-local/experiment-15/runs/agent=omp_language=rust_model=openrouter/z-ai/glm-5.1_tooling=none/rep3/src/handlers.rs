use axum::extract::{Path, Query, State};
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use sqlx::SqlitePool;

use crate::errors::AppError;
use crate::models::{Book, CreateBook, UpdateBook};

pub async fn health() -> &'static str {
    "ok"
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(input): Json<CreateBook>,
) -> Result<impl IntoResponse, AppError> {
    input.validate().map_err(AppError::Validation)?;
    let book = input.into_book();
    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(&book.id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&pool)
    .await?;
    Ok((axum::http::StatusCode::CREATED, Json(book)))
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(params): Query<ListQuery>,
) -> Result<impl IntoResponse, AppError> {
    let books: Vec<Book> = if let Some(author) = params.author {
        sqlx::query_as("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
            .bind(author)
            .fetch_all(&pool)
            .await?
    } else {
        sqlx::query_as("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&pool)
            .await?
    };
    Ok(Json(books))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, AppError> {
    let book: Book = sqlx::query_as("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(&id)
        .fetch_optional(&pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("book {} not found", id)))?;
    Ok(Json(book))
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
    Json(input): Json<UpdateBook>,
) -> Result<impl IntoResponse, AppError> {
    input.validate().map_err(AppError::Validation)?;
    let existing: Book =
        sqlx::query_as("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
            .bind(&id)
            .fetch_optional(&pool)
            .await?
            .ok_or_else(|| AppError::NotFound(format!("book {} not found", id)))?;

    let title = input.title.unwrap_or(existing.title);
    let author = input.author.unwrap_or(existing.author);
    let year = input.year.or(existing.year);
    let isbn = input.isbn.or(existing.isbn);

    sqlx::query("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
        .bind(&title)
        .bind(&author)
        .bind(year)
        .bind(&isbn)
        .bind(&id)
        .execute(&pool)
        .await?;

    let updated: Book =
        sqlx::query_as("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
            .bind(&id)
            .fetch_one(&pool)
            .await?;
    Ok(Json(updated))
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, AppError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&pool)
        .await?;
    if result.rows_affected() == 0 {
        return Err(AppError::NotFound(format!("book {} not found", id)));
    }
    Ok(axum::http::StatusCode::NO_CONTENT)
}
