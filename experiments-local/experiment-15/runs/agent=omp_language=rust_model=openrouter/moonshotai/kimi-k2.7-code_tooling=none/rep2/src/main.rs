use anyhow::{Context, Result};
use axum::{
    Json, Router,
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
};
use rusqlite::{Connection, params};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct AppState {
    db: Arc<Mutex<Connection>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Deserialize)]
struct CreateBook {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Deserialize)]
struct UpdateBook {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
}

#[derive(Debug, Deserialize)]
struct ListBooksQuery {
    author: Option<String>,
}

fn init_db(conn: &Connection) -> Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )",
        [],
    )?;
    Ok(())
}

fn validate_book(title: &str, author: &str) -> Result<(), AppError> {
    if title.trim().is_empty() {
        return Err(AppError::Validation("title is required".to_string()));
    }
    if author.trim().is_empty() {
        return Err(AppError::Validation("author is required".to_string()));
    }
    Ok(())
}

#[derive(Debug)]
enum AppError {
    NotFound,
    Validation(String),
    Internal(anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            AppError::Validation(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::Internal(err) => {
                eprintln!("internal error: {err:?}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "internal server error".to_string(),
                )
            }
        };
        (status, Json(ErrorResponse { error: message })).into_response()
    }
}

impl<E> From<E> for AppError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        AppError::Internal(err.into())
    }
}

async fn health_check() -> impl IntoResponse {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<CreateBook>,
) -> Result<impl IntoResponse, AppError> {
    validate_book(&payload.title, &payload.author)?;

    let db = state.db.lock().map_err(|e| anyhow::anyhow!("{e}"))?;
    db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![&payload.title, &payload.author, payload.year, &payload.isbn],
    )?;
    let id = db.last_insert_rowid();

    let book = Book {
        id,
        title: payload.title,
        author: payload.author,
        year: payload.year,
        isbn: payload.isbn,
    };

    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListBooksQuery>,
) -> Result<impl IntoResponse, AppError> {
    let db = state.db.lock().map_err(|e| anyhow::anyhow!("{e}"))?;

    let mut stmt;
    let rows = match query.author {
        Some(author) => {
            stmt =
                db.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1")?;
            stmt.query_map([author], row_to_book)?
        }
        None => {
            stmt = db.prepare("SELECT id, title, author, year, isbn FROM books")?;
            stmt.query_map([], row_to_book)?
        }
    };

    let mut books = Vec::new();
    for row in rows {
        books.push(row?);
    }

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
    Path(id): Path<i64>,
) -> Result<impl IntoResponse, AppError> {
    let db = state.db.lock().map_err(|e| anyhow::anyhow!("{e}"))?;
    let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map([id], row_to_book)?;

    match rows.next() {
        Some(row) => Ok(Json(row?)),
        None => Err(AppError::NotFound),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> Result<impl IntoResponse, AppError> {
    validate_book(&payload.title, &payload.author)?;

    let db = state.db.lock().map_err(|e| anyhow::anyhow!("{e}"))?;
    let affected = db.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![
            &payload.title,
            &payload.author,
            payload.year,
            &payload.isbn,
            id
        ],
    )?;

    if affected == 0 {
        return Err(AppError::NotFound);
    }

    let book = Book {
        id,
        title: payload.title,
        author: payload.author,
        year: payload.year,
        isbn: payload.isbn,
    };

    Ok(Json(book))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let db = state.db.lock().map_err(|e| anyhow::anyhow!("{e}"))?;
    let affected = db.execute("DELETE FROM books WHERE id = ?1", [id])?;

    if affected == 0 {
        return Err(AppError::NotFound);
    }

    Ok(StatusCode::NO_CONTENT)
}

fn create_app(db: Connection) -> Result<Router> {
    init_db(&db)?;
    let state = AppState {
        db: Arc::new(Mutex::new(db)),
    };
    Ok(Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state))
}

#[tokio::main]
async fn main() -> Result<()> {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Connection::open(&db_path)
        .with_context(|| format!("failed to open database at {db_path}"))?;
    let app = create_app(db)?;

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    println!("Listening on {}", listener.local_addr()?);
    axum::serve(listener, app).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{self, Request, StatusCode};
    use tower::ServiceExt;

    fn test_app() -> Router {
        let db = Connection::open_in_memory().unwrap();
        create_app(db).unwrap()
    }

    fn book_json(title: &str, author: &str, year: i32, isbn: &str) -> String {
        format!(
            r#"{{"title":"{}","author":"{}","year":{},"isbn":"{}"}}"#,
            title, author, year, isbn
        )
    }

    #[tokio::test]
    async fn health_check_returns_ok() {
        let app = test_app();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let app = test_app();

        let create = Request::builder()
            .method(http::Method::POST)
            .uri("/books")
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(book_json(
                "The Hobbit",
                "J.R.R. Tolkien",
                1937,
                "978-0-00-000000-0",
            )))
            .unwrap();
        let response = app.clone().oneshot(create).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);

        let created: Book = serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap(),
        )
        .unwrap();
        assert_eq!(created.title, "The Hobbit");

        let get = Request::builder()
            .uri(format!("/books/{}", created.id))
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(get).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let fetched: Book = serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap(),
        )
        .unwrap();
        assert_eq!(fetched.author, "J.R.R. Tolkien");
    }

    #[tokio::test]
    async fn create_book_rejects_missing_title() {
        let app = test_app();
        let request = Request::builder()
            .method(http::Method::POST)
            .uri("/books")
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(
                r#"{"title":"","author":"Anonymous","year":2020,"isbn":"123"}"#,
            ))
            .unwrap();
        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn list_books_with_author_filter() {
        let app = test_app();

        let create1 = Request::builder()
            .method(http::Method::POST)
            .uri("/books")
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(book_json("Book A", "Alice", 2020, "111")))
            .unwrap();
        app.clone().oneshot(create1).await.unwrap();

        let create2 = Request::builder()
            .method(http::Method::POST)
            .uri("/books")
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(book_json("Book B", "Bob", 2021, "222")))
            .unwrap();
        app.clone().oneshot(create2).await.unwrap();

        let list = Request::builder()
            .uri("/books?author=Alice")
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(list).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let books: Vec<Book> = serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap(),
        )
        .unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].title, "Book A");
    }

    #[tokio::test]
    async fn update_and_delete_book() {
        let app = test_app();

        let create = Request::builder()
            .method(http::Method::POST)
            .uri("/books")
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(book_json("Original", "Author", 2000, "000")))
            .unwrap();
        let response = app.clone().oneshot(create).await.unwrap();
        let created: Book = serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap(),
        )
        .unwrap();

        let update = Request::builder()
            .method(http::Method::PUT)
            .uri(format!("/books/{}", created.id))
            .header(http::header::CONTENT_TYPE, "application/json")
            .body(Body::from(book_json("Updated", "Author", 2001, "001")))
            .unwrap();
        let response = app.clone().oneshot(update).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let delete = Request::builder()
            .method(http::Method::DELETE)
            .uri(format!("/books/{}", created.id))
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(delete).await.unwrap();
        assert_eq!(response.status(), StatusCode::NO_CONTENT);

        let get = Request::builder()
            .uri(format!("/books/{}", created.id))
            .body(Body::empty())
            .unwrap();
        let response = app.oneshot(get).await.unwrap();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }
}
