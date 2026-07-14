use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use books_api::app;
use http_body_util::BodyExt;
use serde_json::Value;
use sqlx::sqlite::SqlitePoolOptions;
use sqlx::SqlitePool;
use tower::ServiceExt;

// Helper: create an in-memory sqlite pool with the schema.
// `sqlite::memory:` gives each connection its own private database, so we
// cap the pool to a single connection to keep the schema visible across
// queries issued by different handlers.
async fn setup_pool() -> SqlitePool {
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect("sqlite::memory:")
        .await
        .unwrap();
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
    .unwrap();
    pool
}

async fn body_json(body: Body) -> Value {
    let bytes = body.collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap_or(Value::Null)
}

async fn send(app: axum::Router, method: Method, uri: &str, body: Option<String>) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let req = if let Some(b) = body {
        builder = builder.header("content-type", "application/json");
        builder.body(Body::from(b)).unwrap()
    } else {
        builder.body(Body::empty()).unwrap()
    };
    let resp = app.oneshot(req).await.unwrap();
    let status = resp.status();
    let b = body_json(resp.into_body()).await;
    (status, b)
}

fn app_with(pool: SqlitePool) -> axum::Router {
    app(pool)
}

#[tokio::test]
async fn create_get_and_delete_book() {
    let pool = setup_pool().await;
    let app = app_with(pool.clone());

    let payload = serde_json::json!({
        "title": "The Rust Book",
        "author": "Steve",
        "year": 2020,
        "isbn": "111-222-333"
    });
    let (st, body) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(payload.to_string()),
    )
    .await;
    assert_eq!(st, StatusCode::CREATED);
    let id = body["id"].as_i64().unwrap();

    // GET single
    let (st, body) = send(app.clone(), Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(st, StatusCode::OK);
    assert_eq!(body["title"], "The Rust Book");
    assert_eq!(body["author"], "Steve");
    assert_eq!(body["year"], 2020);
    assert_eq!(body["isbn"], "111-222-333");

    // DELETE
    let (st, _b) = send(app.clone(), Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(st, StatusCode::NO_CONTENT);

    // GET after delete -> 404
    let (st, _b) = send(app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(st, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_with_author_filter() {
    let pool = setup_pool().await;

    // Seed two books with different authors.
    for (title, author) in [("A1", "Alice"), ("A2", "Bob")] {
        let p = serde_json::json!({ "title": title, "author": author });
        let (_st, _b) = send(
            app_with(pool.clone()),
            Method::POST,
            "/books",
            Some(p.to_string()),
        )
        .await;
    }

    // No filter -> 2 books
    let (st, body) = send(app_with(pool.clone()), Method::GET, "/books", None).await;
    assert_eq!(st, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 2);

    // Filter by author=Alice -> 1
    let (st, body) = send(
        app_with(pool.clone()),
        Method::GET,
        "/books?author=Alice",
        None,
    )
    .await;
    assert_eq!(st, StatusCode::OK);
    let arr = body.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert_eq!(arr[0]["author"], "Alice");
}

#[tokio::test]
async fn validation_rejects_missing_fields() {
    let pool = setup_pool().await;
    let app = app_with(pool);

    // Missing title
    let p = serde_json::json!({ "author": "Someone" });
    let (st, body) = send(app.clone(), Method::POST, "/books", Some(p.to_string())).await;
    assert_eq!(st, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));

    // Empty author
    let p = serde_json::json!({ "title": "T", "author": "   " });
    let (st, body) = send(app, Method::POST, "/books", Some(p.to_string())).await;
    assert_eq!(st, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn health_ok() {
    let pool = setup_pool().await;
    let app = app_with(pool);
    let (st, body) = send(app, Method::GET, "/health", None).await;
    assert_eq!(st, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn update_book_partial() {
    let pool = setup_pool().await;
    let app = app_with(pool.clone());

    let p = serde_json::json!({ "title": "Old", "author": "OldAuth", "year": 1990 });
    let (_st, body) = send(app.clone(), Method::POST, "/books", Some(p.to_string())).await;
    let id = body["id"].as_i64().unwrap();

    // Partial update: only author
    let upd = serde_json::json!({ "author": "NewAuth" });
    let (st, body) = send(
        app.clone(),
        Method::PUT,
        &format!("/books/{id}"),
        Some(upd.to_string()),
    )
    .await;
    assert_eq!(st, StatusCode::OK);
    assert_eq!(body["author"], "NewAuth");
    assert_eq!(body["title"], "Old"); // unchanged
    assert_eq!(body["year"], 1990); // unchanged

    // Empty-string title update rejected
    let upd = serde_json::json!({ "title": "  " });
    let (st, body) = send(
        app,
        Method::PUT,
        &format!("/books/{id}"),
        Some(upd.to_string()),
    )
    .await;
    assert_eq!(st, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));
}
