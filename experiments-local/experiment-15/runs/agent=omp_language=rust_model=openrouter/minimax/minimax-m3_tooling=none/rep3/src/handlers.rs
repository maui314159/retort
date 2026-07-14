//! HTTP handlers for the books API.

use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use serde_json::json;
use sqlx::SqlitePool;

use crate::error::{AppError, AppResult};
use crate::models::{Book, BookUpdate, NewBook};

#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
}

#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub author: Option<String>,
}

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<NewBook>,
) -> AppResult<(StatusCode, Json<Book>)> {
    let validated = payload.validate()?;
    let book = crate::db::create_book(&state.pool, validated).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> AppResult<Json<Vec<Book>>> {
    let author = params
        .author
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty());
    let books = crate::db::list_books(&state.pool, author).await?;
    Ok(Json(books))
}

pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<Json<Book>> {
    let book = crate::db::fetch_book(&state.pool, id)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<BookUpdate>,
) -> AppResult<Json<Book>> {
    let validated = payload.validate()?;
    let book = crate::db::update_book(&state.pool, id, validated)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<StatusCode> {
    let removed = crate::db::delete_book(&state.pool, id).await?;
    if removed {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError::NotFound)
    }
}
