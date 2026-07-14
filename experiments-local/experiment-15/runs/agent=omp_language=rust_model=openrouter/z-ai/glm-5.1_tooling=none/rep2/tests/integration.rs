use axum::body::Body;
use axum::http::{Request, StatusCode};
use http::header;
use serde_json::Value;
use sqlx::SqlitePool;
use tower::ServiceExt;

use book_api::app;

async fn setup() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::query(
        "CREATE TABLE books (
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

fn post_books(body: &str) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/books")
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

fn get(uri: &str) -> Request<Body> {
    Request::builder().uri(uri).body(Body::empty()).unwrap()
}

fn put_books(id: i64, body: &str) -> Request<Body> {
    Request::builder()
        .method("PUT")
        .uri(format!("/books/{id}"))
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

fn delete_books(id: i64) -> Request<Body> {
    Request::builder()
        .method("DELETE")
        .uri(format!("/books/{id}"))
        .body(Body::empty())
        .unwrap()
}

async fn body_to_json(body: Body) -> Value {
    let bytes = axum::body::to_bytes(body, 1024 * 64).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn test_health() {
    let pool = setup().await;
    let svc = app(pool);

    let req = get("/health");
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_to_json(resp.into_body()).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn test_create_and_get_book() {
    let pool = setup().await;
    let svc = app(pool.clone());

    // Create
    let req = post_books(r#"{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}"#);
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let book: Value = body_to_json(resp.into_body()).await;
    assert_eq!(book["title"], "The Hobbit");
    assert_eq!(book["author"], "J.R.R. Tolkien");
    assert_eq!(book["year"], 1937);

    // Get the same book
    let id = book["id"].as_i64().unwrap();
    let svc = app(pool);
    let req = get(&format!("/books/{id}"));
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched: Value = body_to_json(resp.into_body()).await;
    assert_eq!(fetched["title"], "The Hobbit");
    assert_eq!(fetched["id"], id);
}

#[tokio::test]
async fn test_validation_empty_title_and_author() {
    let pool = setup().await;

    // Empty title
    let svc = app(pool.clone());
    let req = post_books(r#"{"title":"","author":"Someone"}"#);
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Empty author
    let svc = app(pool);
    let req = post_books(r#"{"title":"A Book","author":""}"#);
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_list_books_with_author_filter() {
    let pool = setup().await;
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Book A")
        .bind("Alice")
        .bind(2020)
        .execute(&pool)
        .await
        .unwrap();
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Book B")
        .bind("Bob")
        .bind(2021)
        .execute(&pool)
        .await
        .unwrap();

    let svc = app(pool);
    let req = get("/books?author=Alice");
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let books: Value = body_to_json(resp.into_body()).await;
    let arr = books.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert_eq!(arr[0]["author"], "Alice");
}

#[tokio::test]
async fn test_update_book() {
    let pool = setup().await;
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("Old Title")
        .bind("Old Author")
        .bind(2000)
        .execute(&pool)
        .await
        .unwrap();

    let svc = app(pool);
    let req = put_books(1, r#"{"title":"New Title"}"#);
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let book: Value = body_to_json(resp.into_body()).await;
    assert_eq!(book["title"], "New Title");
    assert_eq!(book["author"], "Old Author");
}

#[tokio::test]
async fn test_delete_book() {
    let pool = setup().await;
    sqlx::query("INSERT INTO books (title, author, year) VALUES (?, ?, ?)")
        .bind("To Delete")
        .bind("Author")
        .bind(2022)
        .execute(&pool)
        .await
        .unwrap();

    let svc = app(pool);
    let req = delete_books(1);
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_get_nonexistent_book() {
    let pool = setup().await;
    let svc = app(pool);
    let req = get("/books/9999");
    let resp = svc.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
