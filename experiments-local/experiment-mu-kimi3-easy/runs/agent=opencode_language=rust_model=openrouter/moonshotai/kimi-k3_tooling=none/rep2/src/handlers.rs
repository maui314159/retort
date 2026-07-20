//! HTTP handlers for the book collection API.

use std::sync::Arc;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::{
    db,
    error::ApiError,
    models::{Book, BookInput},
    AppState,
};

/// `GET /health` — liveness probe.
pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

/// Validate the user-supplied fields of a create/update payload.
fn validate(input: &BookInput) -> Result<(), ApiError> {
    if input.title.trim().is_empty() {
        return Err(ApiError::BadRequest("title is required".to_string()));
    }
    if input.author.trim().is_empty() {
        return Err(ApiError::BadRequest("author is required".to_string()));
    }
    Ok(())
}

/// `POST /books` — create a new book.
pub async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate(&input)?;
    let conn = state.db.lock().expect("db mutex poisoned");
    let book = db::create_book(&conn, &input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// Query parameters accepted by `GET /books`.
#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub author: Option<String>,
}

/// `GET /books` — list all books, optionally filtered by `?author=`.
pub async fn list_books(
    State(state): State<Arc<AppState>>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.db.lock().expect("db mutex poisoned");
    Ok(Json(db::list_books(&conn, params.author.as_deref())?))
}

/// `GET /books/{id}` — fetch a single book.
pub async fn get_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.db.lock().expect("db mutex poisoned");
    db::get_book(&conn, id)?
        .map(Json)
        .ok_or_else(|| ApiError::NotFound(format!("book {id} not found")))
}

/// `PUT /books/{id}` — replace all fields of a book.
pub async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    validate(&input)?;
    let conn = state.db.lock().expect("db mutex poisoned");
    db::update_book(&conn, id, &input)?
        .map(Json)
        .ok_or_else(|| ApiError::NotFound(format!("book {id} not found")))
}

/// `DELETE /books/{id}` — remove a book.
pub async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.db.lock().expect("db mutex poisoned");
    if db::delete_book(&conn, id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound(format!("book {id} not found")))
    }
}
