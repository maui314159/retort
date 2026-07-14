use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::Deserialize;
use serde_json::json;

use crate::{
    db,
    error::ApiError,
    models::{validate_required, Book, BookInput, BookUpdate},
    AppState,
};

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn health() -> (StatusCode, Json<serde_json::Value>) {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate_required(&input.title, &input.author)
        .map_err(|e| ApiError::BadRequest(e.message.to_string()))?;

    let conn = state.conn.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = db::insert(
        &conn,
        &input.title,
        &input.author,
        input.year.map(|y| y as i64),
        input.isbn.as_deref(),
    )?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<serde_json::Value>, ApiError> {
    let conn = state.conn.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let books = db::list(&conn, query.author.as_deref())?;
    Ok(Json(json!({ "books": books })))
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.conn.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    match db::get(&conn, id)? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound),
    }
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookUpdate>,
) -> Result<Json<Book>, ApiError> {
    validate_required(&input.title, &input.author)
        .map_err(|e| ApiError::BadRequest(e.message.to_string()))?;

    let conn = state.conn.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    match db::update(
        &conn,
        id,
        &input.title,
        &input.author,
        input.year.map(|y| y as i64),
        input.isbn.as_deref(),
    )? {
        Some(book) => Ok(Json(book)),
        None => Err(ApiError::NotFound),
    }
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.conn.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    if db::delete(&conn, id)? {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound)
    }
}
