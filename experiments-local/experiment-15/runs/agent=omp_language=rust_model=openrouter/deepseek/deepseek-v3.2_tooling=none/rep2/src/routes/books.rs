use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    routing::{delete, get, post, put},
    Json, Router,
};
use serde::Deserialize;
use uuid::Uuid;
use validator::Validate;

use crate::{
    db::repository::BookRepository,
    error::AppError,
    models::{Book, CreateBookRequest, UpdateBookRequest},
};

#[derive(Debug, Deserialize)]
pub struct BookQuery {
    author: Option<String>,
}

pub fn router(pool: crate::db::DbPool) -> Router {
    let repository = BookRepository::new(pool);
    Router::new()
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .with_state(repository)
}

async fn create_book(
    State(repository): State<BookRepository>,
    Json(payload): Json<CreateBookRequest>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    // Validate input
    payload
        .validate()
        .map_err(|e| AppError::Validation(e.to_string()))?;

    let book = Book::new(payload.title, payload.author, payload.year, payload.isbn);
    let created_book = repository.create(&book).await?;

    Ok((StatusCode::CREATED, Json(created_book)))
}

async fn list_books(
    State(repository): State<BookRepository>,
    Query(query): Query<BookQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = repository.find_all(query.author).await?;
    Ok(Json(books))
}

async fn get_book(
    State(repository): State<BookRepository>,
    Path(id): Path<Uuid>,
) -> Result<Json<Book>, AppError> {
    let book = repository
        .find_by_id(id)
        .await?
        .ok_or(AppError::NotFound)?;

    Ok(Json(book))
}

async fn update_book(
    State(repository): State<BookRepository>,
    Path(id): Path<Uuid>,
    Json(payload): Json<UpdateBookRequest>,
) -> Result<Json<Book>, AppError> {
    // Validate input if fields are present
    payload
        .validate()
        .map_err(|e| AppError::Validation(e.to_string()))?;

    let existing_book = repository
        .find_by_id(id)
        .await?
        .ok_or(AppError::NotFound)?;

    let updated_book = Book {
        id,
        title: payload.title.unwrap_or(existing_book.title),
        author: payload.author.unwrap_or(existing_book.author),
        year: payload.year.unwrap_or(existing_book.year),
        isbn: payload.isbn.unwrap_or(existing_book.isbn),
    };

    let book = repository.update(id, &updated_book).await?;
    Ok(Json(book))
}

async fn delete_book(
    State(repository): State<BookRepository>,
    Path(id): Path<Uuid>,
) -> Result<(StatusCode, Json<serde_json::Value>), AppError> {
    let deleted = repository.delete(id).await?;
    if deleted {
        Ok((
            StatusCode::NO_CONTENT,
            Json(serde_json::json!({ "message": "Book deleted" })),
        ))
    } else {
        Err(AppError::NotFound)
    }
}