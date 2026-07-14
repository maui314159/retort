use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;
use sqlx::SqlitePool;

use crate::{error::ApiError, models::{Book, CreateBookRequest, UpdateBookRequest}};

#[derive(Debug, serde::Deserialize)]
pub struct ListBooksQuery {
    author: Option<String>,
}

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok" })))
}

pub async fn create_book(
    State(pool): State<SqlitePool>,
    Json(create_req): Json<CreateBookRequest>,
) -> Result<impl IntoResponse, ApiError> {
    // Validate input
    create_req.validate()
        .map_err(|e| ApiError::ValidationError(e.message().to_string()))?;

    let book = Book::new(create_req);
    
    let saved_book = sqlx::query_as::<_, Book>(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?) RETURNING *"
    )
    .bind(&book.id)
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .fetch_one(&pool)
    .await
    .map_err(ApiError::DatabaseError)?;

    Ok((StatusCode::CREATED, Json(saved_book)))
}

pub async fn list_books(
    State(pool): State<SqlitePool>,
    Query(query): Query<ListBooksQuery>,
) -> Result<impl IntoResponse, ApiError> {
    let books = match query.author {
        Some(author) => {
            sqlx::query_as::<_, Book>("SELECT * FROM books WHERE author = ? ORDER BY title")
                .bind(author)
                .fetch_all(&pool)
                .await
                .map_err(ApiError::DatabaseError)?
        }
        None => {
            sqlx::query_as::<_, Book>("SELECT * FROM books ORDER BY title")
                .fetch_all(&pool)
                .await
                .map_err(ApiError::DatabaseError)?
        }
    };

    Ok((StatusCode::OK, Json(books)))
}

pub async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await
        .map_err(ApiError::DatabaseError)?;

    match book {
        Some(book) => Ok((StatusCode::OK, Json(book))),
        None => Err(ApiError::NotFound),
    }
}

pub async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
    Json(update_req): Json<UpdateBookRequest>,
) -> Result<impl IntoResponse, ApiError> {
    // Validate input
    update_req.validate()
        .map_err(|e| ApiError::ValidationError(e.message().to_string()))?;

    // First, get the existing book
    let mut book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(&id)
        .fetch_optional(&pool)
        .await
        .map_err(ApiError::DatabaseError)?
        .ok_or(ApiError::NotFound)?;

    // Update the book
    book.update(update_req);

    // Save the updated book
    let updated_book = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? RETURNING *"
    )
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .bind(&id)
    .fetch_one(&pool)
    .await
    .map_err(ApiError::DatabaseError)?;

    Ok((StatusCode::OK, Json(updated_book)))
}

pub async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&pool)
        .await
        .map_err(ApiError::DatabaseError)?;

    if result.rows_affected() == 0 {
        return Err(ApiError::NotFound);
    }

    Ok((StatusCode::NO_CONTENT, ()))
}