use crate::error::AppError;
use crate::models::{Book, BookInput};
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::{Json, Router};
use serde::Deserialize;
use sqlx::SqlitePool;

#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(state)
}

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({ "status": "ok" })))
}

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = if let Some(author) = q.author {
        let author = author.trim().to_string();
        if author.is_empty() {
            sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .fetch_all(&state.pool)
                .await?
        } else {
            sqlx::query_as::<_, Book>(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )
            .bind(author)
            .fetch_all(&state.pool)
            .await?
        }
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .fetch_all(&state.pool)
            .await?
    };
    Ok(Json(books))
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let (title, author, year, isbn) = input.validated().map_err(AppError::BadRequest)?;
    let book = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)
         RETURNING id, title, author, year, isbn",
    )
    .bind(title)
    .bind(author)
    .bind(year)
    .bind(isbn)
    .fetch_one(&state.pool)
    .await?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, AppError> {
    let (title, author, year, isbn) = input.validated().map_err(AppError::BadRequest)?;
    let book = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4
         WHERE id = ?5
         RETURNING id, title, author, year, isbn",
    )
    .bind(title)
    .bind(author)
    .bind(year)
    .bind(isbn)
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let res = sqlx::query("DELETE FROM books WHERE id = ?1")
        .bind(id)
        .execute(&state.pool)
        .await?;
    if res.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}
