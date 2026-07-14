use std::sync::Arc;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ErrorBody {
    pub error: String,
}

#[derive(Debug)]
pub enum ApiError {
    NotFound,
    Validation(String),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::NotFound => (
                StatusCode::NOT_FOUND,
                ErrorBody {
                    error: "book not found".to_string(),
                },
            ),
            ApiError::Validation(msg) => (StatusCode::BAD_REQUEST, ErrorBody { error: msg }),
            ApiError::Internal(msg) => {
                (StatusCode::INTERNAL_SERVER_ERROR, ErrorBody { error: msg })
            }
        };
        (status, Json(body)).into_response()
    }
}

#[derive(Clone)]
pub struct AppState {
    pub db: Arc<std::sync::Mutex<Connection>>,
}

impl AppState {
    pub fn new(conn: Connection) -> Self {
        Self {
            db: Arc::new(std::sync::Mutex::new(conn)),
        }
    }
}

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
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

pub fn create_book(state: &AppState, input: CreateBook) -> Result<Book, ApiError> {
    let title = input.title.trim().to_string();
    let author = input.author.trim().to_string();
    if title.is_empty() {
        return Err(ApiError::Validation("title is required".to_string()));
    }
    if author.is_empty() {
        return Err(ApiError::Validation("author is required".to_string()));
    }
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(format!("db lock error: {}", e)))?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, input.year, input.isbn],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title,
        author,
        year: input.year,
        isbn: input.isbn,
    })
}

pub fn list_books(state: &AppState, author_filter: Option<String>) -> Result<Vec<Book>, ApiError> {
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(format!("db lock error: {}", e)))?;
    let mut books = Vec::new();
    if let Some(author) = author_filter {
        let mut stmt = conn
            .prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map(params![author], |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            })
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        for r in rows {
            books.push(r.map_err(|e| ApiError::Internal(e.to_string()))?);
        }
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map([], |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            })
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        for r in rows {
            books.push(r.map_err(|e| ApiError::Internal(e.to_string()))?);
        }
    }
    Ok(books)
}

pub fn get_book(state: &AppState, id: i64) -> Result<Book, ApiError> {
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(format!("db lock error: {}", e)))?;
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        },
    )
    .map_err(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
        other => ApiError::Internal(other.to_string()),
    })
}

pub fn update_book(state: &AppState, id: i64, input: UpdateBook) -> Result<Book, ApiError> {
    if let Some(ref title) = input.title {
        if title.trim().is_empty() {
            return Err(ApiError::Validation("title cannot be empty".to_string()));
        }
    }
    if let Some(ref author) = input.author {
        if author.trim().is_empty() {
            return Err(ApiError::Validation("author cannot be empty".to_string()));
        }
    }
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(format!("db lock error: {}", e)))?;
    let existing: Option<Book> = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            },
        )
        .ok();
    let mut current = match existing {
        Some(b) => b,
        None => return Err(ApiError::NotFound),
    };
    if let Some(t) = input.title {
        current.title = t.trim().to_string();
    }
    if let Some(a) = input.author {
        current.author = a.trim().to_string();
    }
    if let Some(y) = input.year {
        current.year = Some(y);
    }
    if let Some(i) = input.isbn {
        current.isbn = Some(i);
    }
    let changed = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![current.title, current.author, current.year, current.isbn, id],
        )
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(current)
}

pub fn delete_book(state: &AppState, id: i64) -> Result<(), ApiError> {
    let conn = state
        .db
        .lock()
        .map_err(|e| ApiError::Internal(format!("db lock error: {}", e)))?;
    let changed = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if changed == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(())
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

async fn create_handler(
    State(state): State<AppState>,
    Json(input): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let book = create_book(&state, input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_handler(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = list_books(&state, q.author)?;
    Ok(Json(books))
}

async fn get_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let book = get_book(&state, id)?;
    Ok(Json(book))
}

async fn update_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, ApiError> {
    let book = update_book(&state, id, input)?;
    Ok(Json(book))
}

async fn delete_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    delete_book(&state, id)?;
    Ok(StatusCode::NO_CONTENT)
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_handler).get(list_handler))
        .route(
            "/books/{id}",
            get(get_handler).put(update_handler).delete(delete_handler),
        )
        .with_state(state)
}

pub fn open_connection(path: &str) -> rusqlite::Result<Connection> {
    let conn = Connection::open(path)?;
    init_db(&conn)?;
    Ok(conn)
}

#[cfg(test)]
mod tests;
