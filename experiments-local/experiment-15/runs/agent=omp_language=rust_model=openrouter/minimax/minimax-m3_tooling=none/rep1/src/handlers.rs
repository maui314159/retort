use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::{
    error::ApiError,
    models::{Book, BookInput},
    state::AppState,
};

/// `GET /health` — lightweight liveness probe.
pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

/// `POST /books` — create a new book.
pub async fn create_book(
    State(state): State<AppState>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let Json(input) = payload.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    input.validate()?;

    let book = Book::new(input);
    sqlx::query(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(&book.id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .execute(&state.pool)
    .await?;

    Ok((StatusCode::CREATED, Json(book)))
}

/// Query string for `GET /books`.
#[derive(Debug, Default, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// `GET /books` — list all books, optionally filtered by author.
pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = if let Some(author) = query.author.filter(|a| !a.is_empty()) {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books \
             WHERE author = ? ORDER BY title COLLATE NOCASE",
        )
        .bind(author)
        .fetch_all(&state.pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books \
             ORDER BY title COLLATE NOCASE",
        )
        .fetch_all(&state.pool)
        .await?
    };
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch a single book.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Book>, ApiError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(ApiError::NotFound)?;
    Ok(Json(book))
}

/// `PUT /books/{id}` — replace an existing book.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    payload: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let Json(input) = payload.map_err(|e| ApiError::BadRequest(e.body_text()))?;
    input.validate()?;

    let result = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&input.title)
    .bind(&input.author)
    .bind(input.year)
    .bind(&input.isbn)
    .bind(&id)
    .execute(&state.pool)
    .await?;

    if result.rows_affected() == 0 {
        return Err(ApiError::NotFound);
    }

    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_one(&state.pool)
    .await?;

    Ok(Json(book))
}

/// `DELETE /books/{id}` — remove a book.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&state.pool)
        .await?;

    if result.rows_affected() == 0 {
        return Err(ApiError::NotFound);
    }

    Ok(StatusCode::NO_CONTENT)
}
