//! HTTP handlers for the book collection API.

use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::Json;
use serde::Deserialize;
use sqlx::{Pool, Sqlite};

use crate::error::{AppError, AppResult};
use crate::model::{Book, BookCreate, BookUpdate};

/// Shared application state: a SQLite connection pool.
#[derive(Clone)]
pub struct AppState {
    pub pool: Pool<Sqlite>,
}

/// Query parameters for `GET /books`.
#[derive(Debug, Default, Deserialize)]
pub struct ListParams {
    /// If present, only books whose `author` contains this substring are returned.
    pub author: Option<String>,
}

/// Liveness probe. Always returns 200 with a small JSON body.
pub async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

/// `POST /books` — create a new book.
pub async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<BookCreate>,
) -> AppResult<(StatusCode, Json<Book>)> {
    let validated = payload.validate()?;
    let row = sqlx::query_as::<_, BookRow>(
        r#"INSERT INTO books (title, author, year, isbn)
           VALUES (?1, ?2, ?3, ?4)
           RETURNING id, title, author, year, isbn, created_at, updated_at"#,
    )
    .bind(&validated.title)
    .bind(&validated.author)
    .bind(validated.year)
    .bind(&validated.isbn)
    .fetch_one(&state.pool)
    .await?;

    Ok((StatusCode::CREATED, Json(row.into_book())))
}

/// `GET /books` — list books, optionally filtered by `?author=`.
pub async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> AppResult<Json<Vec<Book>>> {
    let rows: Vec<BookRow> =
        match params.author.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
            Some(filter) => {
                let like = format!("%{}%", filter);
                sqlx::query_as::<_, BookRow>(
                    r#"SELECT id, title, author, year, isbn, created_at, updated_at
                       FROM books
                       WHERE author LIKE ?1 COLLATE NOCASE
                       ORDER BY id ASC"#,
                )
                .bind(like)
                .fetch_all(&state.pool)
                .await?
            }
            None => {
                sqlx::query_as::<_, BookRow>(
                    r#"SELECT id, title, author, year, isbn, created_at, updated_at
                       FROM books
                       ORDER BY id ASC"#,
                )
                .fetch_all(&state.pool)
                .await?
            }
        };

    let books: Vec<Book> = rows.into_iter().map(BookRow::into_book).collect();
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch a single book.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<Json<Book>> {
    let row = sqlx::query_as::<_, BookRow>(
        r#"SELECT id, title, author, year, isbn, created_at, updated_at
           FROM books WHERE id = ?1"#,
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::NotFound)?;

    Ok(Json(row.into_book()))
}

/// `PUT /books/{id}` — replace an existing book.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<BookUpdate>,
) -> AppResult<Json<Book>> {
    let validated = payload.validate()?;

    let row = sqlx::query_as::<_, BookRow>(
        r#"UPDATE books
           SET title = ?1,
               author = ?2,
               year = ?3,
               isbn = ?4,
               updated_at = datetime('now')
           WHERE id = ?5
           RETURNING id, title, author, year, isbn, created_at, updated_at"#,
    )
    .bind(&validated.title)
    .bind(&validated.author)
    .bind(validated.year)
    .bind(&validated.isbn)
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::NotFound)?;

    Ok(Json(row.into_book()))
}

/// `DELETE /books/{id}` — remove a book. Returns 204 on success, 404 if absent.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<StatusCode> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?1")
        .bind(id)
        .execute(&state.pool)
        .await?;

    if result.rows_affected() == 0 {
        Err(AppError::NotFound)
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

/// Internal row type for `sqlx::query_as!`/`query_as`.
///
/// The `chrono` types in `Book` already implement `Type`/`Decode`/`Encode`
/// for SQLite when the `chrono` feature is enabled, so we can map directly.
#[derive(Debug, sqlx::FromRow)]
struct BookRow {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
    created_at: chrono::DateTime<chrono::Utc>,
    updated_at: chrono::DateTime<chrono::Utc>,
}

impl BookRow {
    fn into_book(self) -> Book {
        let BookRow {
            id,
            title,
            author,
            year,
            isbn,
            created_at,
            updated_at,
        } = self;
        Book {
            id,
            title,
            author,
            year,
            isbn,
            created_at,
            updated_at,
        }
    }
}
