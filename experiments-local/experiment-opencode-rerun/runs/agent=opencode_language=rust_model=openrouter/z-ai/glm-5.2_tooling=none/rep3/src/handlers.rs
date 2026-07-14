use std::sync::Arc;

use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;
use serde_json::json;

use crate::db;
use crate::error::AppError;
use crate::models::{Book, CreateBook, UpdateBook};
use crate::state::AppState;

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(input): Json<CreateBook>,
) -> Result<impl IntoResponse, AppError> {
    input.validate().map_err(AppError::BadRequest)?;

    let book = {
        let conn = state.conn.lock().map_err(|e| AppError::Internal(e.to_string()))?;
        db::insert_book(&conn, &input)?
    };
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(state): State<Arc<AppState>>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = {
        let conn = state.conn.lock().map_err(|e| AppError::Internal(e.to_string()))?;
        db::list_books(&conn, q.author.as_deref())?
    };
    Ok(Json(books))
}

pub async fn get_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = {
        let conn = state.conn.lock().map_err(|e| AppError::Internal(e.to_string()))?;
        db::get_book(&conn, id)?.ok_or(AppError::NotFound)?
    };
    Ok(Json(book))
}

pub async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    input.validate().map_err(AppError::BadRequest)?;

    let book = {
        let conn = state.conn.lock().map_err(|e| AppError::Internal(e.to_string()))?;
        db::update_book(&conn, id, &input)?.ok_or(AppError::NotFound)?
    };
    Ok(Json(book))
}

pub async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, AppError> {
    let deleted = {
        let conn = state.conn.lock().map_err(|e| AppError::Internal(e.to_string()))?;
        db::delete_book(&conn, id)?
    };
    if deleted {
        Ok((StatusCode::NO_CONTENT, Json(json!({}))))
    } else {
        Err(AppError::NotFound)
    }
}
