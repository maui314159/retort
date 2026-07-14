use std::sync::Arc;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing, Json, Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct AppState {
    pub conn: Arc<Mutex<Connection>>,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: u32,
    pub title: String,
    pub author: String,
    pub year: Option<u32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<u32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListBooksQuery {
    pub author: Option<String>,
}

#[derive(Debug)]
pub enum ApiError {
    Database(rusqlite::Error),
    NotFound,
    Validation(String),
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::Database(err)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::Database(err) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": err.to_string()})),
            )
                .into_response(),
            ApiError::NotFound => StatusCode::NOT_FOUND.into_response(),
            ApiError::Validation(msg) => {
                (StatusCode::BAD_REQUEST, Json(json!({"error": msg}))).into_response()
            }
        }
    }
}

pub fn init_db(conn: &Connection) -> Result<(), rusqlite::Error> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(())
}

pub fn app() -> Router {
    let conn = Connection::open_in_memory().expect("open in-memory database");
    init_db(&conn).expect("initialize database");
    let state = AppState {
        conn: Arc::new(Mutex::new(conn)),
    };
    build_app(state)
}

pub fn build_app(state: AppState) -> Router {
    Router::new()
        .route("/health", routing::get(health))
        .route("/books", routing::get(list_books).post(create_book))
        .route(
            "/books/{id}",
            routing::get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({"status": "ok"}))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListBooksQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.conn.lock().await;
    let mut stmt =
        conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1)")?;
    let author_param = query.author.as_deref();
    let books = stmt
        .query_map([author_param], map_row)?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<u32>,
) -> Result<Json<Book>, ApiError> {
    let conn = state.conn.lock().await;
    let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map([i64::from(id)], map_row)?;
    let book = rows.next().ok_or(ApiError::NotFound)??;
    Ok(Json(book))
}

async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let title = validate_required(payload.title, "title")?;
    let author = validate_required(payload.author, "author")?;

    let conn = state.conn.lock().await;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![&title, &author, payload.year.map(i64::from), payload.isbn],
    )?;
    let id = conn.last_insert_rowid() as u32;

    Ok((
        StatusCode::CREATED,
        Json(Book {
            id,
            title,
            author,
            year: payload.year,
            isbn: payload.isbn,
        }),
    ))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<u32>,
    Json(payload): Json<CreateBook>,
) -> Result<Json<Book>, ApiError> {
    let title = validate_required(payload.title, "title")?;
    let author = validate_required(payload.author, "author")?;

    let conn = state.conn.lock().await;
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![&title, &author, payload.year.map(i64::from), payload.isbn, i64::from(id)],
    )?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }

    Ok(Json(Book {
        id,
        title,
        author,
        year: payload.year,
        isbn: payload.isbn,
    }))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<u32>,
) -> Result<StatusCode, ApiError> {
    let conn = state.conn.lock().await;
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", [i64::from(id)])?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

fn validate_required(value: Option<String>, field: &str) -> Result<String, ApiError> {
    match value {
        Some(v) if !v.trim().is_empty() => Ok(v.trim().to_owned()),
        _ => Err(ApiError::Validation(format!("{field} is required"))),
    }
}

fn map_row(row: &rusqlite::Row) -> Result<Book, rusqlite::Error> {
    Ok(Book {
        id: row.get::<_, i64>(0)? as u32,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get::<_, Option<i64>>(3)?.map(|y| y as u32),
        isbn: row.get(4)?,
    })
}
