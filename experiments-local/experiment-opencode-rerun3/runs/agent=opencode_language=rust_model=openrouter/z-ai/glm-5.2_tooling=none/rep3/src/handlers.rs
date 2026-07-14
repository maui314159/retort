use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::Deserialize;
use sqlx::SqlitePool;

use crate::error::AppError;
use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(input): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    input.validate().map_err(AppError::BadRequest)?;

    let created = sqlx::query_as::<_, Book>(
        r#"
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
        RETURNING id, title, author, year, isbn, created_at
        "#,
    )
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year)
    .bind(input.isbn.as_deref())
    .fetch_one(&pool)
    .await?;

    Ok((StatusCode::CREATED, Json(created)))
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = if let Some(author) = q.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn, created_at FROM books WHERE author = ? ORDER BY id",
        )
        .bind(author)
        .fetch_all(&pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn, created_at FROM books ORDER BY id",
        )
        .fetch_all(&pool)
        .await?
    };
    Ok(Json(books))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn, created_at FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&pool)
    .await?
    .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    input.validate().map_err(AppError::BadRequest)?;

    let existing = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn, created_at FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&pool)
    .await?
    .ok_or(AppError::NotFound)?;

    let title = input.title.unwrap_or(existing.title);
    let author = input.author.unwrap_or(existing.author);
    let year = input.year.or(existing.year);
    let isbn = input.isbn.or(existing.isbn);

    let updated = sqlx::query_as::<_, Book>(
        r#"
        UPDATE books
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
        RETURNING id, title, author, year, isbn, created_at
        "#,
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(isbn.as_deref())
    .bind(id)
    .fetch_one(&pool)
    .await?;

    Ok(Json(updated))
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await?;

    if result.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

pub async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}
