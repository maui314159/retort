use crate::db::{self, Db};
use crate::error::AppError;
use crate::models::{Book, CreateBook, UpdateBook};
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    input.validate().map_err(AppError::Validation)?;
    let book = db::create_book(&db, &input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = db::list_books(&db, query.author.as_deref())?;
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = db::get_book(&db, id)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let book = db::update_book(&db, id, &input)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    db::delete_book(&db, id)?;
    Ok(StatusCode::NO_CONTENT)
}

pub async fn health() -> impl IntoResponse {
    let body = serde_json::json!({ "status": "ok" });
    (StatusCode::OK, Json(body)).into_response()
}
