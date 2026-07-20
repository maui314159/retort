//! HTTP handlers for the book collection API.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::{db, models::BookInput};

/// Application state shared by all handlers.
pub struct AppState {
    pub conn: Mutex<Connection>,
}

type SharedState = Arc<AppState>;
type ApiResponse = (StatusCode, Json<Value>);

fn error(status: StatusCode, message: &str) -> ApiResponse {
    (status, Json(json!({ "error": message })))
}

/// Validate that title and author are present and non-blank.
fn validate(input: &BookInput) -> Result<(&str, &str), ApiResponse> {
    let title = input.title.as_deref().map(str::trim).unwrap_or_default();
    if title.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "title is required"));
    }
    let author = input.author.as_deref().map(str::trim).unwrap_or_default();
    if author.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "author is required"));
    }
    Ok((title, author))
}

/// GET /health — liveness probe.
pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

/// POST /books — create a new book.
pub async fn create_book(
    State(state): State<SharedState>,
    Json(input): Json<BookInput>,
) -> ApiResponse {
    let (title, author) = match validate(&input) {
        Ok(valid) => valid,
        Err(resp) => return resp,
    };
    let conn = state.conn.lock().expect("database mutex poisoned");
    match db::create_book(&conn, title, author, input.year, input.isbn.as_deref()) {
        Ok(book) => (StatusCode::CREATED, Json(json!(book))),
        Err(_) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "failed to create book",
        ),
    }
}

/// Query parameters accepted by `GET /books`.
#[derive(Debug, Deserialize)]
pub struct ListParams {
    author: Option<String>,
}

/// GET /books — list all books, optionally filtered by `?author=`.
pub async fn list_books(
    State(state): State<SharedState>,
    Query(params): Query<ListParams>,
) -> ApiResponse {
    let conn = state.conn.lock().expect("database mutex poisoned");
    match db::list_books(&conn, params.author.as_deref()) {
        Ok(books) => (StatusCode::OK, Json(json!(books))),
        Err(_) => error(StatusCode::INTERNAL_SERVER_ERROR, "failed to list books"),
    }
}

/// GET /books/{id} — fetch a single book.
pub async fn get_book(State(state): State<SharedState>, Path(id): Path<i64>) -> ApiResponse {
    let conn = state.conn.lock().expect("database mutex poisoned");
    match db::get_book(&conn, id) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(_) => error(StatusCode::INTERNAL_SERVER_ERROR, "failed to fetch book"),
    }
}

/// PUT /books/{id} — replace a book's fields.
pub async fn update_book(
    State(state): State<SharedState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> ApiResponse {
    let (title, author) = match validate(&input) {
        Ok(valid) => valid,
        Err(resp) => return resp,
    };
    let conn = state.conn.lock().expect("database mutex poisoned");
    match db::update_book(&conn, id, title, author, input.year, input.isbn.as_deref()) {
        Ok(Some(book)) => (StatusCode::OK, Json(json!(book))),
        Ok(None) => error(StatusCode::NOT_FOUND, "book not found"),
        Err(_) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "failed to update book",
        ),
    }
}

/// DELETE /books/{id} — remove a book.
pub async fn delete_book(State(state): State<SharedState>, Path(id): Path<i64>) -> StatusCode {
    let conn = state.conn.lock().expect("database mutex poisoned");
    match db::delete_book(&conn, id) {
        Ok(true) => StatusCode::NO_CONTENT,
        Ok(false) => StatusCode::NOT_FOUND,
        Err(_) => StatusCode::INTERNAL_SERVER_ERROR,
    }
}
