//! Integration tests: drive the real axum router over an in-memory SQLite
//! database using `tower::oneshot`, so no TCP port or running server is
//! required.

use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    Router,
};
use book_api::{build_router, db, AppState};
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

/// Fresh app with an empty in-memory database per test.
fn test_app() -> Router {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    db::init_schema(&conn).expect("init schema");
    build_router(AppState::new(conn))
}

fn request(method: &str, uri: &str, body: Option<Value>) -> Request<Body> {
    let body = match body {
        Some(v) => Body::from(v.to_string()),
        None => Body::empty(),
    };
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(body)
        .unwrap()
}

/// Send a request, returning the status code and parsed JSON body
/// (`Value::Null` for empty bodies such as 204 responses).
async fn call(app: &Router, req: Request<Body>) -> (StatusCode, Value) {
    let resp = app.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let body = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("response is valid JSON")
    };
    (status, body)
}

async fn create_book(app: &Router, title: &str, author: &str) -> Value {
    let (status, body) = call(
        app,
        request(
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "create failed: {body}");
    body
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = test_app();
    let (status, body) = call(&app, request("GET", "/health", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_and_get_book_roundtrip() {
    let app = test_app();

    let (status, created) = call(
        &app,
        request(
            "POST",
            "/books",
            Some(json!({
                "title": "The Rust Programming Language",
                "author": "Steve Klabnik",
                "year": 2018,
                "isbn": "978-1593278281"
            })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(created["title"], "The Rust Programming Language");
    assert_eq!(created["author"], "Steve Klabnik");
    assert_eq!(created["year"], 2018);
    assert_eq!(created["isbn"], "978-1593278281");
    let id = created["id"].as_i64().expect("id assigned");

    let (status, fetched) = call(&app, request("GET", &format!("/books/{id}"), None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched, created);
}

#[tokio::test]
async fn create_book_rejects_missing_or_blank_required_fields() {
    let app = test_app();

    // Missing title.
    let (status, body) = call(
        &app,
        request("POST", "/books", Some(json!({ "author": "Someone" }))),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    // Blank author.
    let (status, body) = call(
        &app,
        request(
            "POST",
            "/books",
            Some(json!({ "title": "T", "author": "   " })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author must not be empty");

    // Validation failures must not create rows.
    let (status, body) = call(&app, request("GET", "/books", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!([]));
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = test_app();
    create_book(&app, "Dune", "Frank Herbert").await;
    create_book(&app, "Dune Messiah", "Frank Herbert").await;
    create_book(&app, "Neuromancer", "William Gibson").await;

    // Unfiltered: all three.
    let (status, body) = call(&app, request("GET", "/books", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    // Filtered: only Frank Herbert's books.
    let (status, body) = call(&app, request("GET", "/books?author=Frank%20Herbert", None)).await;
    assert_eq!(status, StatusCode::OK);
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Frank Herbert"));

    // Filter matching nothing: empty list, not an error.
    let (status, body) = call(&app, request("GET", "/books?author=Nobody", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!([]));
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = test_app();
    let created = create_book(&app, "Old Title", "Old Author").await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = call(
        &app,
        request(
            "PUT",
            &format!("/books/{id}"),
            Some(json!({
                "title": "New Title",
                "author": "New Author",
                "year": 2024
            })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["id"], id);
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["author"], "New Author");
    assert_eq!(updated["year"], 2024);

    // Persisted: a fresh GET shows the new values.
    let (status, fetched) = call(&app, request("GET", &format!("/books/{id}"), None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched["title"], "New Title");

    // Updating a nonexistent book is a 404.
    let (status, _) = call(
        &app,
        request(
            "PUT",
            "/books/9999",
            Some(json!({ "title": "X", "author": "Y" })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Invalid payloads are rejected with 400.
    let (status, _) = call(
        &app,
        request(
            "PUT",
            &format!("/books/{id}"),
            Some(json!({ "author": "Y" })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = test_app();
    let created = create_book(&app, "Bye", "Author").await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = call(&app, request("DELETE", &format!("/books/{id}"), None)).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = call(&app, request("GET", &format!("/books/{id}"), None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Deleting again is a 404, not a 204.
    let (status, _) = call(&app, request("DELETE", &format!("/books/{id}"), None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404_json_error() {
    let app = test_app();
    let (status, body) = call(&app, request("GET", "/books/42", None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body["error"].as_str().unwrap().contains("42"));
}
