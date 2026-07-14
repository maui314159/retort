use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions, SqliteRow};
use sqlx::{Row, SqlitePool as Pool};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::str::FromStr;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct NewBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    error: String,
}

#[derive(Debug)]
struct ApiError(pub StatusCode, pub String);

impl From<sqlx::Error> for ApiError {
    fn from(e: sqlx::Error) -> Self {
        ApiError(StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let body = Json(ErrorBody { error: self.1 });
        (self.0, body).into_response()
    }
}

type AppState = Pool;

fn validate_title_author(title: &str, author: &str) -> Result<(), ApiError> {
    if title.trim().is_empty() {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "title is required".to_string(),
        ));
    }
    if author.trim().is_empty() {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "author is required".to_string(),
        ));
    }
    Ok(())
}

fn row_to_book(row: &SqliteRow) -> Result<Book, ApiError> {
    Ok(Book {
        id: row.try_get("id")?,
        title: row.try_get("title")?,
        author: row.try_get("author")?,
        year: row.try_get("year")?,
        isbn: row.try_get("isbn")?,
    })
}

async fn create_book(
    State(pool): State<AppState>,
    Json(input): Json<NewBook>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate_title_author(&input.title, &input.author)?;
    let row = sqlx::query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) \
         RETURNING id, title, author, year, isbn",
    )
    .bind(input.title)
    .bind(input.author)
    .bind(input.year)
    .bind(input.isbn.as_deref())
    .fetch_one(&pool)
    .await?;
    let book = row_to_book(&row)?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(pool): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let rows = if let Some(author) = params.get("author") {
        sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?")
            .bind(format!("%{}%", author))
            .fetch_all(&pool)
            .await?
    } else {
        sqlx::query("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&pool)
            .await?
    };
    let mut books = Vec::new();
    for row in rows.iter() {
        books.push(row_to_book(row)?);
    }
    Ok(Json(books))
}

async fn get_book(
    State(pool): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let row = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await?;
    match row {
        Some(row) => Ok(Json(row_to_book(&row)?)),
        None => Err(ApiError(
            StatusCode::NOT_FOUND,
            format!("book {} not found", id),
        )),
    }
}

async fn update_book(
    State(pool): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<UpdateBook>,
) -> Result<Json<Book>, ApiError> {
    let existing = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await?;
    let existing = match existing {
        Some(row) => row_to_book(&row)?,
        None => {
            return Err(ApiError(
                StatusCode::NOT_FOUND,
                format!("book {} not found", id),
            ))
        }
    };
    let new_title = input.title.unwrap_or(existing.title);
    let new_author = input.author.unwrap_or(existing.author);
    let new_year = input.year.or(existing.year);
    let new_isbn = input.isbn.or(existing.isbn);
    validate_title_author(&new_title, &new_author)?;
    let row = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? \
         RETURNING id, title, author, year, isbn",
    )
    .bind(new_title)
    .bind(new_author)
    .bind(new_year)
    .bind(new_isbn.as_deref())
    .bind(id)
    .fetch_one(&pool)
    .await?;
    Ok(Json(row_to_book(&row)?))
}

async fn delete_book(
    State(pool): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let res = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await?;
    if res.rows_affected() == 0 {
        Err(ApiError(
            StatusCode::NOT_FOUND,
            format!("book {} not found", id),
        ))
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

async fn health() -> &'static str {
    "ok"
}

pub async fn make_pool(url: &str) -> Result<Pool, sqlx::Error> {
    let opts = SqliteConnectOptions::from_str(url)?
        .create_if_missing(true)
        .foreign_keys(false)
        .shared_cache(true);
    // In-memory databases are private per-connection unless shared cache is
    // used; keep a single connection to guarantee all queries hit the same DB.
    let max_conn = if url.contains(":memory:") { 1 } else { 5 };
    let pool = SqlitePoolOptions::new()
        .max_connections(max_conn)
        .connect_with(opts)
        .await?;
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (\
            id INTEGER PRIMARY KEY AUTOINCREMENT,\
            title TEXT NOT NULL,\
            author TEXT NOT NULL,\
            year INTEGER,\
            isbn TEXT\
        )",
    )
    .execute(&pool)
    .await?;
    Ok(pool)
}

pub fn app(pool: Pool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(pool)
}

pub async fn serve() -> Result<(), Box<dyn std::error::Error>> {
    let url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db".to_string());
    let pool = make_pool(&url).await?;
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("listening on {addr}");
    axum::serve(listener, app(pool)).await?;
    Ok(())
}
