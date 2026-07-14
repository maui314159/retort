use axum::{extract::{Path, Query, State}, http::StatusCode, Json};
use sqlx::SqlitePool;
use uuid::Uuid;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest, ListBooksQuery};
use crate::db;

pub async fn health_check() -> &'static str {
    "OK"
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(req): Json<CreateBookRequest>,
) -> Result<(StatusCode, Json<Book>), StatusCode> {
    if req.title.trim().is_empty() || req.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let book = db::create_book(&pool, req).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(query): Query<ListBooksQuery>,
) -> Result<Json<Vec<Book>>, StatusCode> {
    let books = db::list_books(&pool, query.author).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(books))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<Uuid>,
) -> Result<Json<Book>, StatusCode> {
    let book = db::get_book(&pool, id).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(book.ok_or(StatusCode::NOT_FOUND)?))
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<Json<Book>, StatusCode> {
    if let Some(title) = &req.title {
        if title.trim().is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
    }
    if let Some(author) = &req.author {
        if author.trim().is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
    }

    let book = db::update_book(&pool, id, req).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok(Json(book.ok_or(StatusCode::NOT_FOUND)?))
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<Uuid>,
) -> Result<StatusCode, StatusCode> {
    let deleted = db::delete_book(&pool, id).await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}
