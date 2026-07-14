use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ErrorBody {
    pub error: String,
}

pub type DbPool = Pool<SqliteConnectionManager>;

pub struct AppState {
    pub pool: DbPool,
}

impl Clone for AppState {
    fn clone(&self) -> Self {
        AppState {
            pool: self.pool.clone(),
        }
    }
}

#[derive(Debug)]
pub struct AppError(pub StatusCode, pub String);

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        (self.0, Json(ErrorBody { error: self.1 })).into_response()
    }
}

impl From<rusqlite::Error> for AppError {
    fn from(e: rusqlite::Error) -> Self {
        AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
    }
}

pub fn init_db(pool: &DbPool) -> Result<(), rusqlite::Error> {
    let conn = pool.get().map_err(|e| {
        rusqlite::Error::SqliteFailure(
            rusqlite::ffi::Error::new(0),
            Some(format!("pool error: {}", e)),
        )
    })?;
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

fn validate(input: &BookInput) -> Result<(), AppError> {
    if input.title.trim().is_empty() {
        return Err(AppError(StatusCode::BAD_REQUEST, "title is required".into()));
    }
    if input.author.trim().is_empty() {
        return Err(AppError(StatusCode::BAD_REQUEST, "author is required".into()));
    }
    Ok(())
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    validate(&input)?;
    let pool = state.pool;
    let book = tokio::task::spawn_blocking(move || -> Result<Book, AppError> {
        let conn = pool
            .get()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![
                input.title.trim(),
                input.author.trim(),
                input.year,
                input.isbn.as_deref(),
            ],
        )
        .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let id = conn.last_insert_rowid();
        Ok(Book {
            id,
            title: input.title.trim().to_string(),
            author: input.author.trim().to_string(),
            year: input.year,
            isbn: input.isbn,
        })
    })
    .await
    .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))??;
    Ok((StatusCode::CREATED, Json(book)))
}

#[derive(Deserialize)]
struct ListQuery {
    author: Option<String>,
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let pool = state.pool;
    let author = q.author;
    let books = tokio::task::spawn_blocking(move || -> Result<Vec<Book>, AppError> {
        let conn = pool
            .get()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let stmt = if let Some(a) = author {
            let mut s = conn
                .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
            let rows = s
                .query_map(rusqlite::params![a], row_to_book)
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        } else {
            let mut s = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
            let rows = s
                .query_map([], row_to_book)
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        };
        Ok(stmt)
    })
    .await
    .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))??;
    Ok(Json(books))
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

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let pool = state.pool;
    let book = tokio::task::spawn_blocking(move || -> Result<Option<Book>, AppError> {
        let conn = pool
            .get()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let mut rows = stmt
            .query(rusqlite::params![id])
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        if let Some(r) = rows
            .next()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        {
            Ok(Some(Book {
                id: r.get(0)?,
                title: r.get(1)?,
                author: r.get(2)?,
                year: r.get(3)?,
                isbn: r.get(4)?,
            }))
        } else {
            Ok(None)
        }
    })
    .await
    .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))??;
    match book {
        Some(b) => Ok(Json(b)),
        None => Err(AppError(StatusCode::NOT_FOUND, "book not found".into())),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, AppError> {
    validate(&input)?;
    let pool = state.pool;
    let book = tokio::task::spawn_blocking(move || -> Result<Option<Book>, AppError> {
        let conn = pool
            .get()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let affected = conn
            .execute(
                "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
                rusqlite::params![
                    input.title.trim(),
                    input.author.trim(),
                    input.year,
                    input.isbn.as_deref(),
                    id,
                ],
            )
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        if affected == 0 {
            return Ok(None);
        }
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let mut rows = stmt
            .query(rusqlite::params![id])
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        if let Some(r) = rows
            .next()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        {
            Ok(Some(Book {
                id: r.get(0)?,
                title: r.get(1)?,
                author: r.get(2)?,
                year: r.get(3)?,
                isbn: r.get(4)?,
            }))
        } else {
            Ok(None)
        }
    })
    .await
    .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))??;
    match book {
        Some(b) => Ok(Json(b)),
        None => Err(AppError(StatusCode::NOT_FOUND, "book not found".into())),
    }
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let pool = state.pool;
    let deleted = tokio::task::spawn_blocking(move || -> Result<bool, AppError> {
        let conn = pool
            .get()
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        let affected = conn
            .execute("DELETE FROM books WHERE id = ?1", rusqlite::params![id])
            .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        Ok(affected > 0)
    })
    .await
    .map_err(|e| AppError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))??;
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError(StatusCode::NOT_FOUND, "book not found".into()))
    }
}

async fn health() -> Json<HashMap<&'static str, &'static str>> {
    let mut m = HashMap::new();
    m.insert("status", "ok");
    Json(m)
}

pub fn build_app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

pub fn make_pool(path: &str) -> DbPool {
    let manager = SqliteConnectionManager::file(path);
    r2d2::Pool::builder()
        .build(manager)
        .expect("failed to create pool")
}
