use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use sqlx::SqlitePool;

use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(input): Json<CreateBook>,
) -> impl IntoResponse {
    if let Err(e) = input.validate() {
        return (StatusCode::BAD_REQUEST, Json(serde_json::json!({ "error": e }))).into_response();
    }

    let result = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn",
    )
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year)
    .bind(&input.isbn)
    .fetch_one(&pool)
    .await;

    match result {
        Ok(book) => (StatusCode::CREATED, Json(book)).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(query): Query<ListQuery>,
) -> impl IntoResponse {
    let books = if let Some(author) = query.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
        )
        .bind(author)
        .fetch_all(&pool)
        .await
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&pool)
            .await
    };

    match books {
        Ok(b) => Json(b).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> impl IntoResponse {
    let result = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&pool)
    .await;

    match result {
        Ok(Some(book)) => Json(book).into_response(),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "book not found" })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> impl IntoResponse {
    // Fetch existing
    let existing = match sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&pool)
    .await
    {
        Ok(Some(b)) => b,
        Ok(None) => {
            return (
                StatusCode::NOT_FOUND,
                Json(serde_json::json!({ "error": "book not found" })),
            )
                .into_response()
        }
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": e.to_string() })),
            )
                .into_response()
        }
    };

    // Validate: title and author must remain non-empty if provided
    let title = input.title.unwrap_or(existing.title);
    let author = input.author.unwrap_or(existing.author);
    if title.trim().is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({ "error": "title is required" })),
        )
            .into_response();
    }
    if author.trim().is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({ "error": "author is required" })),
        )
            .into_response();
    }

    let year = input.year.or(existing.year);
    let isbn = input.isbn.or(existing.isbn);

    let result = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id, title, author, year, isbn",
    )
    .bind(&title)
    .bind(&author)
    .bind(year)
    .bind(&isbn)
    .bind(id)
    .fetch_one(&pool)
    .await;

    match result {
        Ok(book) => Json(book).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> impl IntoResponse {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await;

    match result {
        Ok(r) if r.rows_affected() > 0 => StatusCode::NO_CONTENT.into_response(),
        Ok(_) => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "book not found" })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}
