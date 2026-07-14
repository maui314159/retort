use anyhow::{Context, Result};
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    db: Arc<Mutex<Connection>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

fn init_db(conn: &Connection) -> Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )
    .context("failed to create books table")?;
    Ok(())
}

pub fn create_app(db_path: &str) -> Result<Router> {
    let conn = Connection::open(db_path).context("failed to open SQLite database")?;
    init_db(&conn)?;
    let state = AppState {
        db: Arc::new(Mutex::new(conn)),
    };

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book).get(list_books))
        .route("/books/:id", get(get_book).put(update_book).delete(delete_book))
        .with_state(state);

    Ok(app)
}

async fn health_check(State(state): State<AppState>) -> Response {
    let check = state
        .db
        .lock()
        .map_err(|e| format!("lock error: {e}"))
        .and_then(|conn| conn.query_row("SELECT 1", [], |_| Ok(())).map_err(|e| format!("db error: {e}")));

    match check {
        Ok(()) => (StatusCode::OK, "OK").into_response(),
        Err(msg) => {
            eprintln!("health check failed: {msg}");
            (StatusCode::SERVICE_UNAVAILABLE, "unhealthy").into_response()
        }
    }
}

fn validate_create(input: &CreateBook) -> Result<(), AppError> {
    let title = input.title.as_deref().unwrap_or("").trim();
    if title.is_empty() {
        return Err(AppError::Validation("title is required".to_string()));
    }
    let author = input.author.as_deref().unwrap_or("").trim();
    if author.is_empty() {
        return Err(AppError::Validation("author is required".to_string()));
    }
    Ok(())
}

fn validate_update(input: &UpdateBook) -> Result<(), AppError> {
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
    Ok(())
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<CreateBook>,
) -> Result<Response, AppError> {
    validate_create(&input)?;

    let id = Uuid::new_v4().to_string();
    let title = input.title.clone().unwrap_or_default();
    let author = input.author.clone().unwrap_or_default();
    let conn = state.db.lock().map_err(|_| AppError::Internal("db lock poisoned".to_string()))?;
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![&id, &title, &author, input.year, input.isbn],
    )
    .context("failed to insert book")?;

    let book = Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    };

    Ok((StatusCode::CREATED, Json(book)).into_response())
}

async fn list_books(
    State(state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, AppError> {
    let conn = state.db.lock().map_err(|_| AppError::Internal("db lock poisoned".to_string()))?;

    let books = if let Some(author) = params.get("author") {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY title")
            .context("failed to prepare filtered select")?;
        let rows = stmt
            .query_map([author], row_to_book)
            .context("failed to query books by author")?;
        rows.collect::<Result<Vec<_>, _>>()
            .context("failed to collect books")?
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY title")
            .context("failed to prepare select")?;
        let rows = stmt
            .query_map([], row_to_book)
            .context("failed to query books")?;
        rows.collect::<Result<Vec<_>, _>>()
            .context("failed to collect books")?
    };

    Ok(Json(books))
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Response, AppError> {
    let conn = state.db.lock().map_err(|_| AppError::Internal("db lock poisoned".to_string()))?;
    let mut stmt = conn
        .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
        .context("failed to prepare get book")?;
    let mut rows = stmt
        .query_map([&id], row_to_book)
        .context("failed to query book")?;

    match rows.next() {
        Some(Ok(book)) => Ok((StatusCode::OK, Json(book)).into_response()),
        Some(Err(e)) => Err(AppError::Internal(e.to_string())),
        None => Ok(not_found("book not found")),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(input): Json<UpdateBook>,
) -> Result<Response, AppError> {
    validate_update(&input)?;

    let conn = state.db.lock().map_err(|_| AppError::Internal("db lock poisoned".to_string()))?;

    conn.execute(
        "UPDATE books SET
            title = COALESCE(?2, title),
            author = COALESCE(?3, author),
            year = COALESCE(?4, year),
            isbn = COALESCE(?5, isbn)
         WHERE id = ?1",
        params![&id, input.title, input.author, input.year, input.isbn],
    )
    .context("failed to update book")?;

    if conn.changes() == 0 {
        return Ok(not_found("book not found"));
    }

    let mut stmt = conn
        .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
        .context("failed to prepare select updated book")?;
    let mut rows = stmt
        .query_map([&id], row_to_book)
        .context("failed to query updated book")?;

    match rows.next() {
        Some(Ok(book)) => Ok((StatusCode::OK, Json(book)).into_response()),
        Some(Err(e)) => Err(AppError::Internal(e.to_string())),
        None => Ok(not_found("book not found")),
    }
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Response, AppError> {
    let conn = state.db.lock().map_err(|_| AppError::Internal("db lock poisoned".to_string()))?;
    conn.execute("DELETE FROM books WHERE id = ?1", [&id])
        .context("failed to delete book")?;

    if conn.changes() == 0 {
        return Ok(not_found("book not found"));
    }

    Ok(StatusCode::NO_CONTENT.into_response())
}

fn not_found(message: &str) -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(ErrorResponse {
            error: message.to_string(),
        }),
    )
        .into_response()
}

#[derive(Debug)]
pub enum AppError {
    Validation(String),
    Internal(String),
}

impl From<anyhow::Error> for AppError {
    fn from(err: anyhow::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        match self {
            AppError::Validation(msg) => (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse { error: msg }),
            )
                .into_response(),
            AppError::Internal(msg) => {
                eprintln!("internal error: {msg}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(ErrorResponse {
                        error: "internal server error".to_string(),
                    }),
                )
                    .into_response()
            }
        }
    }
}
