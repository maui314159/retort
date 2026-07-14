use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Deserialize;
use sqlx::SqlitePool;

use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

#[derive(Debug)]
pub enum ApiError {
    NotFound,
    Validation(String),
    Db(sqlx::Error),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::NotFound => (StatusCode::NOT_FOUND, "not found".to_string()),
            ApiError::Validation(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::Db(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
        };
        let body = serde_json::json!({ "error": msg });
        (status, Json(body)).into_response()
    }
}

impl From<sqlx::Error> for ApiError {
    fn from(e: sqlx::Error) -> Self {
        if let sqlx::Error::RowNotFound = e {
            ApiError::NotFound
        } else {
            ApiError::Db(e)
        }
    }
}

pub async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = payload.validate().map_err(ApiError::Validation)?;

    let row = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)
         RETURNING id, title, author, year, isbn",
    )
    .bind(title)
    .bind(author)
    .bind(payload.year)
    .bind(payload.isbn)
    .fetch_one(&pool)
    .await?;

    Ok((StatusCode::CREATED, Json(row)))
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let rows = if let Some(author) = q.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
        )
        .bind(author)
        .fetch_all(&pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&pool)
            .await?
    };

    Ok(Json(rows))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let row = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_one(&pool)
    .await?;

    Ok(Json(row))
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, ApiError> {
    let payload = payload.into_validated().map_err(ApiError::Validation)?;

    let current: Book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_one(&pool)
    .await?;

    let title = payload.title.unwrap_or(current.title);
    let author = payload.author.unwrap_or(current.author);
    let year = payload.year.or(current.year);
    let isbn = payload.isbn.or(current.isbn);

    let row = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?
         WHERE id = ?
         RETURNING id, title, author, year, isbn",
    )
    .bind(title)
    .bind(author)
    .bind(year)
    .bind(isbn)
    .bind(id)
    .fetch_one(&pool)
    .await?;

    Ok(Json(row))
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let res = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await?;

    if res.rows_affected() == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
