use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde::Deserialize;
use serde_json::json;

use crate::db::{self, DbPool};
use crate::error::{AppError, AppResult};
use crate::models::{Book, CreateBook, UpdateBook};

/// Shared application state — just the database pool.
#[derive(Clone)]
pub struct AppState {
    pub pool: DbPool,
}

/// `GET /health` — returns 200 when the service is up and the DB is reachable.
pub async fn health(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    // Touch the database to confirm connectivity.
    let conn = state.pool.get().map_err(|e| AppError::Pool(e.to_string()))?;
    conn.execute_batch("SELECT 1;")
        .map_err(AppError::Database)?;
    Ok(Json(json!({ "status": "ok" })))
}

#[derive(Debug, Deserialize, Default)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// `POST /books` — create a book.
pub async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<CreateBook>,
) -> AppResult<(StatusCode, Json<Book>)> {
    payload
        .validate()
        .map_err(AppError::Validation)?;
    let book = db::insert_book(&state.pool, &payload)?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// `GET /books?author=` — list books, optionally filtered by author substring.
pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> AppResult<Json<Vec<Book>>> {
    let books = db::list_books(&state.pool, query.author.as_deref())?;
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch a single book.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<Json<Book>> {
    let book = db::get_book_by_id(&state.pool, id)?;
    Ok(Json(book))
}

/// `PUT /books/{id}` — update a book. Only provided fields are changed.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> AppResult<Json<Book>> {
    payload
        .validate()
        .map_err(AppError::Validation)?;
    let book = db::update_book(&state.pool, id, &payload)?;
    Ok(Json(book))
}

/// `DELETE /books/{id}` — delete a book. Returns 204 on success.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<StatusCode> {
    db::delete_book(&state.pool, id)?;
    Ok(StatusCode::NO_CONTENT)
}
