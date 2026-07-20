//! HTTP handlers — thin adapters between axum extractors and the db layer.

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

/// Query parameters accepted by `GET /books`.
#[derive(Debug, Deserialize)]
pub struct ListParams {
    author: Option<String>,
}

/// `POST /books` — create a book. 201 on success, 400 on invalid input.
pub async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    input.validate().map_err(ApiError::BadRequest)?;
    let conn = state.conn();
    let book = db::insert_book(&conn, &input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

/// `GET /books` — list all books, optionally filtered by `?author=`.
pub async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.conn();
    let books = db::list_books(&conn, params.author.as_deref())?;
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch one book. 404 when it does not exist.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.conn();
    db::get_book(&conn, id)?
        .map(Json)
        .ok_or_else(|| ApiError::NotFound(format!("book with id {id} not found")))
}

/// `PUT /books/{id}` — replace a book. 404 when missing, 400 on invalid input.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    input.validate().map_err(ApiError::BadRequest)?;
    let conn = state.conn();
    db::update_book(&conn, id, &input)?
        .map(Json)
        .ok_or_else(|| ApiError::NotFound(format!("book with id {id} not found")))
}

/// `DELETE /books/{id}` — remove a book. 204 on success, 404 when missing.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.conn();
    if db::delete_book(&conn, id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound(format!("book with id {id} not found")))
    }
}
