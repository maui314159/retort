use crate::error::ApiError;
use crate::models::{Book, BookInput};
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use sqlx::SqlitePool;

pub fn app_routes(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(pool)
}

async fn health() -> (StatusCode, &'static str) {
    (StatusCode::OK, "ok")
}

async fn create_book(
    State(pool): State<SqlitePool>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let input = input.validate().map_err(ApiError::Validation)?;

    let row = sqlx::query_as::<_, Book>(
        r#"
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
        RETURNING id, title, author, year, isbn, created_at, updated_at
        "#,
    )
    .bind(input.title)
    .bind(input.author)
    .bind(input.year)
    .bind(input.isbn)
    .fetch_one(&pool)
    .await?;

    Ok((StatusCode::CREATED, Json(row)))
}

#[derive(Debug, Deserialize, Default)]
struct ListQuery {
    author: Option<String>,
}

async fn list_books(
    State(pool): State<SqlitePool>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = if let Some(author) = q.author {
        let pattern = format!("%{}%", author.trim());
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books WHERE author LIKE ? ORDER BY id ASC",
        )
        .bind(pattern)
        .fetch_all(&pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn, created_at, updated_at
             FROM books ORDER BY id ASC",
        )
        .fetch_all(&pool)
        .await?
    };
    Ok(Json(books))
}

async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_one(&pool)
    .await?;
    Ok(Json(book))
}

async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let input = input.validate().map_err(ApiError::Validation)?;

    let book = sqlx::query_as::<_, Book>(
        r#"
        UPDATE books
        SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now')
        WHERE id = ?
        RETURNING id, title, author, year, isbn, created_at, updated_at
        "#,
    )
    .bind(input.title)
    .bind(input.author)
    .bind(input.year)
    .bind(input.isbn)
    .bind(id)
    .fetch_one(&pool)
    .await?;

    Ok(Json(book))
}

async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let result =
        sqlx::query("DELETE FROM books WHERE id = ?").bind(id).execute(&pool).await?;
    if result.rows_affected() == 0 {
        return Err(ApiError::NotFound("book not found".to_string()));
    }
    Ok(StatusCode::NO_CONTENT)
}
