use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePool, FromRow, Sqlite, Pool};
use std::collections::HashMap;

#[derive(Debug, Serialize, FromRow)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateBook {
    title: String,
    author: String,
    year: Option<i64>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpdateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i64>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookQuery {
    author: Option<String>,
}

#[derive(Debug, Serialize)]
struct ApiError {
    error: String,
}

enum AppError {
    NotFound,
    Validation(String),
    Internal(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            AppError::Validation(m) => (StatusCode::BAD_REQUEST, m),
            AppError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(ApiError { error: msg })).into_response()
    }
}

type AppState = Pool<Sqlite>;

fn validate_create(input: &CreateBook) -> Result<(), AppError> {
    if input.title.trim().is_empty() {
        return Err(AppError::Validation("title is required".into()));
    }
    if input.author.trim().is_empty() {
        return Err(AppError::Validation("author is required".into()));
    }
    Ok(())
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    validate_create(&input)?;
    let rec = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn",
    )
    .bind(input.title.trim())
    .bind(input.author.trim())
    .bind(input.year)
    .bind(input.isbn.as_deref().map(|s| s.trim()).filter(|s| !s.is_empty()))
    .fetch_one(&state)
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?;
    Ok((StatusCode::CREATED, Json(rec)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<BookQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = if let Some(author) = q.author {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? ORDER BY id",
        )
        .bind(format!("%{}%", author))
        .fetch_all(&state)
        .await
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .fetch_all(&state)
            .await
    }
    .map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&state)
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?
    .ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let existing = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&state)
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?
    .ok_or(AppError::NotFound)?;

    let title = input.title.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    let author = input.author.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());

    if let Some(ref t) = title {
        if t.is_empty() {
            return Err(AppError::Validation("title cannot be empty".into()));
        }
    }
    if let Some(ref a) = author {
        if a.is_empty() {
            return Err(AppError::Validation("author cannot be empty".into()));
        }
    }

    let new_title = title.unwrap_or(existing.title);
    let new_author = author.unwrap_or(existing.author);
    let new_year = input.year.or(existing.year);
    let new_isbn = input.isbn.or(existing.isbn);

    let rec = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id, title, author, year, isbn",
    )
    .bind(new_title)
    .bind(new_author)
    .bind(new_year)
    .bind(new_isbn)
    .bind(id)
    .fetch_one(&state)
    .await
    .map_err(|e| AppError::Internal(e.to_string()))?;
    Ok(Json(rec))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let res = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state)
        .await
        .map_err(|e| AppError::Internal(e.to_string()))?;
    if res.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

async fn health() -> Json<HashMap<&'static str, &'static str>> {
    let mut m = HashMap::new();
    m.insert("status", "ok");
    Json(m)
}

pub async fn build_router(pool: Pool<Sqlite>) -> Router {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(&pool)
    .await
    .expect("create table");

    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(pool)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db".to_string());
    let pool = SqlitePool::connect(&url).await?;
    let app = build_router(pool).await;
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    tracing::info!("listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await?;
    Ok(())
}
