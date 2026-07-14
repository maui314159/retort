use anyhow::Result;
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use sqlx::{Pool, Sqlite};
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
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpdateBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookQuery {
    author: Option<String>,
}

#[derive(Debug)]
struct AppError {
    status: StatusCode,
    message: String,
}

impl AppError {
    fn new(status: StatusCode, message: impl Into<String>) -> Self {
        Self {
            status,
            message: message.into(),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let body = serde_json::json!({ "error": self.message });
        (self.status, Json(body)).into_response()
    }
}

impl From<sqlx::Error> for AppError {
    fn from(e: sqlx::Error) -> Self {
        match e {
            sqlx::Error::RowNotFound => {
                AppError::new(StatusCode::NOT_FOUND, "book not found")
            }
            _ => AppError::new(
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("database error: {e}"),
            ),
        }
    }
}

type AppState = Pool<Sqlite>;

async fn create_schema(pool: &Pool<Sqlite>) -> Result<()> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        "#,
    )
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn build_router(pool: Pool<Sqlite>) -> Result<Router> {
    create_schema(&pool).await?;
    let app = Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(pool);
    Ok(app)
}

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<CreateBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let title = payload
        .title
        .as_ref()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| AppError::new(StatusCode::BAD_REQUEST, "title is required"))?;
    let author = payload
        .author
        .as_ref()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| AppError::new(StatusCode::BAD_REQUEST, "author is required"))?;

    let result = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind(&title)
        .bind(&author)
        .bind(payload.year)
        .bind(payload.isbn.as_deref())
        .execute(&state)
        .await?;

    let id = result.last_insert_rowid();
    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state)
        .await?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<BookQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let books = if let Some(author) = q.author.as_deref() {
        sqlx::query_as::<_, Book>("SELECT * FROM books WHERE author = ? ORDER BY id")
            .bind(author)
            .fetch_all(&state)
            .await?
    } else {
        sqlx::query_as::<_, Book>("SELECT * FROM books ORDER BY id")
            .fetch_all(&state)
            .await?
    };
    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state)
        .await?;
    Ok(Json(book))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let existing = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state)
        .await?;

    let title = match payload.title.as_deref() {
        Some(s) if !s.trim().is_empty() => s.trim().to_string(),
        Some(_) => return Err(AppError::new(StatusCode::BAD_REQUEST, "title cannot be empty")),
        None => existing.title,
    };
    let author = match payload.author.as_deref() {
        Some(s) if !s.trim().is_empty() => s.trim().to_string(),
        Some(_) => {
            return Err(AppError::new(
                StatusCode::BAD_REQUEST,
                "author cannot be empty",
            ))
        }
        None => existing.author,
    };
    let year = payload.year.or(existing.year);
    let isbn = payload.isbn.or(existing.isbn);

    sqlx::query("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
        .bind(&title)
        .bind(&author)
        .bind(year)
        .bind(&isbn)
        .bind(id)
        .execute(&state)
        .await?;

    let book = sqlx::query_as::<_, Book>("SELECT * FROM books WHERE id = ?")
        .bind(id)
        .fetch_one(&state)
        .await?;
    Ok(Json(book))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state)
        .await?;
    if result.rows_affected() == 0 {
        return Err(AppError::new(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}

pub async fn make_pool(url: &str) -> Result<Pool<Sqlite>> {
    let options = SqliteConnectOptions::from_str(url)?.create_if_missing(true);
    let pool = SqlitePoolOptions::new().max_connections(5).connect_with(options).await?;
    Ok(pool)
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();

    let db_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db".to_string());
    let pool = make_pool(&db_url).await?;
    let app = build_router(pool).await?;

    let addr = std::env::var("LISTEN_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!("listening on {addr}");
    axum::serve(listener, app).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::Request;
    use tower::ServiceExt;

    async fn setup() -> Router {
        let pool = make_pool("sqlite::memory:").await.unwrap();
        build_router(pool).await.unwrap()
    }

    #[tokio::test]
    async fn health_ok() {
        let app = setup().await;
        let resp = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(v["status"], "ok");
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let app = setup().await;
        let create = serde_json::json!({
            "title": "The Rust Book",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "9781593278282"
        });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(create.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let book: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let id = book["id"].as_i64().unwrap();

        let app2 = app.clone();
        let resp = app2
            .oneshot(
                Request::builder()
                    .uri(format!("/books/{id}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let got: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(got["title"], "The Rust Book");
        assert_eq!(got["author"], "Steve Klabnik");
    }

    #[tokio::test]
    async fn validation_requires_title_and_author() {
        let app = setup().await;
        let bad = serde_json::json!({ "title": "", "author": "" });
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(bad.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn list_with_author_filter() {
        let app = setup().await;
        for (title, author) in [
            ("A", "Alice"),
            ("B", "Bob"),
            ("C", "Alice"),
        ] {
            let payload = serde_json::json!({ "title": title, "author": author });
            app.clone()
                .oneshot(
                    Request::builder()
                        .method("POST")
                        .uri("/books")
                        .header("content-type", "application/json")
                        .body(Body::from(payload.to_string()))
                        .unwrap(),
                )
                .await
                .unwrap();
        }
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/books?author=Alice")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let arr: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
        assert_eq!(arr.len(), 2);
        for b in &arr {
            assert_eq!(b["author"], "Alice");
        }
    }

    #[tokio::test]
    async fn update_then_delete() {
        let app = setup().await;
        let create = serde_json::json!({ "title": "Old", "author": "Auth" });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(create.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let id: i64 = serde_json::from_slice::<serde_json::Value>(&body).unwrap()["id"]
            .as_i64()
            .unwrap();

        let upd = serde_json::json!({ "title": "New Title" });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("PUT")
                    .uri(format!("/books/{id}"))
                    .header("content-type", "application/json")
                    .body(Body::from(upd.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(v["title"], "New Title");
        assert_eq!(v["author"], "Auth");

        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("DELETE")
                    .uri(format!("/books/{id}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NO_CONTENT);

        let resp = app
            .oneshot(
                Request::builder()
                    .uri(format!("/books/{id}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

}
