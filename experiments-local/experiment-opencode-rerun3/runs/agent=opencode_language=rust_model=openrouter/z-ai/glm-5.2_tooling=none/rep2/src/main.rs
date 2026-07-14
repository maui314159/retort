use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
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
    BadRequest(String),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            ApiError::NotFound => (
                StatusCode::NOT_FOUND,
                ErrorBody { error: "not found".to_string() },
            ),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, ErrorBody { error: msg }),
            ApiError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, ErrorBody { error: msg }),
        };
        (status, Json(body)).into_response()
    }
}

pub type Db = Arc<Mutex<Connection>>;

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year  INTEGER,
            isbn  TEXT
        )",
        [],
    )?;
    Ok(())
}

pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

pub async fn health() -> (StatusCode, Json<serde_json::Value>) {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

pub fn validate_input(input: &BookInput) -> Result<(), ApiError> {
    if input.title.trim().is_empty() {
        return Err(ApiError::BadRequest("title is required".into()));
    }
    if input.author.trim().is_empty() {
        return Err(ApiError::BadRequest("author is required".into()));
    }
    Ok(())
}

pub async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate_input(&input)?;
    let book = insert_book(&db, &input)?;
    Ok((StatusCode::CREATED, Json(book)))
}

pub fn insert_book(db: &Db, input: &BookInput) -> Result<Book, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![
            input.title.trim(),
            input.author.trim(),
            input.year,
            input.isbn.as_deref(),
        ],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: input.title.trim().to_string(),
        author: input.author.trim().to_string(),
        year: input.year,
        isbn: input.isbn.clone(),
    })
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let books = if let Some(author) = q.author {
        let pattern = format!("%{}%", author);
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1 ORDER BY id")
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map(rusqlite::params![pattern], row_to_book)
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect::<Vec<_>>()
    } else {
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        let rows = stmt
            .query_map([], row_to_book)
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        rows.filter_map(|r| r.ok()).collect::<Vec<_>>()
    };
    Ok(Json(books))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            rusqlite::params![id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
            other => ApiError::Internal(other.to_string()),
        })?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookUpdate>,
) -> Result<Json<Book>, ApiError> {
    if let (Some(t), _) = (&input.title, ()) {
        if t.trim().is_empty() {
            return Err(ApiError::BadRequest("title cannot be empty".into()));
        }
    }
    if let Some(a) = &input.author {
        if a.trim().is_empty() {
            return Err(ApiError::BadRequest("author cannot be empty".into()));
        }
    }

    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let existing: Book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            rusqlite::params![id],
            row_to_book,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => ApiError::NotFound,
            other => ApiError::Internal(other.to_string()),
        })?;

    let title = input.title.unwrap_or(existing.title);
    let author = input.author.unwrap_or(existing.author);
    let year = input.year.or(existing.year);
    let isbn = input.isbn.or(existing.isbn);

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, year, isbn, id],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;

    Ok(Json(Book {
        id,
        title,
        author,
        year,
        isbn,
    }))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = db.lock().map_err(|e| ApiError::Internal(e.to_string()))?;
    let affected = conn
        .execute("DELETE FROM books WHERE id = ?1", rusqlite::params![id])
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if affected == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

#[cfg(not(test))]
pub fn make_db(path: &str) -> Db {
    let conn = Connection::open(path).expect("open db");
    init_db(&conn).expect("init db");
    Arc::new(Mutex::new(conn))
}

#[cfg(not(test))]
#[tokio::main]
async fn main() {
    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = make_db(&db_path);
    let addr: std::net::SocketAddr = ([0, 0, 0, 0], 3000).into();
    println!("listening on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app(db)).await.unwrap();
}
