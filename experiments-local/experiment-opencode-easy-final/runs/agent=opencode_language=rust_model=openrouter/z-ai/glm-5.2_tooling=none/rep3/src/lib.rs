use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use sqlx::{Pool, Sqlite};
use std::net::SocketAddr;
use std::str::FromStr;

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateBook {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl CreateBook {
    fn validate(&self) -> Result<(), AppError> {
        if self.title.trim().is_empty() {
            return Err(AppError::Validation("title is required".into()));
        }
        if self.author.trim().is_empty() {
            return Err(AppError::Validation("author is required".into()));
        }
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
struct UpdateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

impl UpdateBook {
    fn validate(&self) -> Result<(), AppError> {
        if let Some(t) = &self.title {
            if t.trim().is_empty() {
                return Err(AppError::Validation("title cannot be empty".into()));
            }
        }
        if let Some(a) = &self.author {
            if a.trim().is_empty() {
                return Err(AppError::Validation("author cannot be empty".into()));
            }
        }
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
struct ListQuery {
    author: Option<String>,
}

#[derive(Debug)]
enum AppError {
    Validation(String),
    NotFound,
    Database(sqlx::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, msg) = match self {
            AppError::Validation(m) => (StatusCode::BAD_REQUEST, m),
            AppError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            AppError::Database(e) => {
                eprintln!("database error: {:?}", e);
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "internal server error".to_string(),
                )
            }
        };
        (status, Json(serde_json::json!({ "error": msg }))).into_response()
    }
}

impl From<sqlx::Error> for AppError {
    fn from(e: sqlx::Error) -> Self {
        match e {
            sqlx::Error::RowNotFound => AppError::NotFound,
            other => AppError::Database(other),
        }
    }
}

#[derive(Clone)]
struct AppState {
    pool: Pool<Sqlite>,
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({ "status": "ok" })))
}

async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    payload.validate()?;
    let row = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id, title, author, year, isbn",
    )
    .bind(&payload.title)
    .bind(&payload.author)
    .bind(payload.year)
    .bind(payload.isbn.as_deref())
    .fetch_one(&state.pool)
    .await?;
    Ok((StatusCode::CREATED, Json(row)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let rows = if let Some(author) = q.author.as_deref() {
        sqlx::query_as::<_, Book>(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
        )
        .bind(author)
        .fetch_all(&state.pool)
        .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .fetch_all(&state.pool)
            .await?
    };
    Ok(Json(rows))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let row = sqlx::query_as::<_, Book>(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_one(&state.pool)
    .await?;
    Ok(Json(row))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    payload.validate()?;
    let row = sqlx::query_as::<_, Book>(
        "UPDATE books SET
            title = COALESCE(?, title),
            author = COALESCE(?, author),
            year = COALESCE(?, year),
            isbn = COALESCE(?, isbn)
         WHERE id = ?
         RETURNING id, title, author, year, isbn",
    )
    .bind(payload.title.as_deref())
    .bind(payload.author.as_deref())
    .bind(payload.year)
    .bind(payload.isbn.as_deref())
    .bind(id)
    .fetch_one(&state.pool)
    .await?;
    Ok(Json(row))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let rows_affected = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.pool)
        .await?
        .rows_affected();
    if rows_affected == 0 {
        return Err(AppError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

async fn migrate(pool: &Pool<Sqlite>) -> sqlx::Result<()> {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn build_app(pool: Pool<Sqlite>) -> Router {
    let state = AppState { pool };
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

pub async fn make_pool(url: &str) -> sqlx::Result<Pool<Sqlite>> {
    let options = SqliteConnectOptions::from_str(url)?
        .create_if_missing(true)
        .foreign_keys(false);
    let pool = SqlitePoolOptions::new()
        .max_connections(8)
        .connect_with(options)
        .await?;
    migrate(&pool).await?;
    Ok(pool)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db".into());
    let pool = make_pool(&database_url).await?;
    let app = build_app(pool).await;

    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("listening on {}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}
