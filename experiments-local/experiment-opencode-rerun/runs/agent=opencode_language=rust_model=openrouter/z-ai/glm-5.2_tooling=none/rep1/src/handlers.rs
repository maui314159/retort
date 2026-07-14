use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde::Deserialize;

use crate::db::Db;
use crate::error::{AppError, AppResult};
use crate::models::{Book, CreateBook, UpdateBook};

#[derive(Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn health() -> AppResult<Json<serde_json::Value>> {
    Ok(Json(serde_json::json!({ "status": "ok" })))
}

pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<CreateBook>,
) -> AppResult<(StatusCode, Json<Book>)> {
    input.validate().map_err(AppError::Validation)?;
    let book = db.create(&input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> AppResult<Json<Vec<Book>>> {
    let books = db.list(q.author.as_deref())?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> AppResult<Json<Book>> {
    let book = db.get(id)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> AppResult<Json<Book>> {
    if let Some(title) = &input.title {
        if title.trim().is_empty() {
            return Err(AppError::Validation("title cannot be empty".to_string()));
        }
    }
    if let Some(author) = &input.author {
        if author.trim().is_empty() {
            return Err(AppError::Validation("author cannot be empty".to_string()));
        }
    }
    let book = db.update(id, &input)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> AppResult<StatusCode> {
    db.delete(id)?;
    Ok(StatusCode::NO_CONTENT)
}
