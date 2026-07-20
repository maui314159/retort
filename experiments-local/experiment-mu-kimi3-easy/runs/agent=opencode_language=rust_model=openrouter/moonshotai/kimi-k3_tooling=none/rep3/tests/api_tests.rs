//! Integration tests for the book collection REST API.
//!
//! Each test builds a fresh app backed by an in-memory SQLite database and
//! drives the router directly with `tower::ServiceExt::oneshot`, so no port
//! binding is required.

use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    Router,
};
use book_api::build_app;
use rusqlite::Connection;
use serde_json::{json, Value};
use tower::ServiceExt;

fn app() -> Router {
    build_app(Connection::open_in_memory().unwrap())
}

fn request(method: &str, uri: &str, body: Option<Value>) -> Request<Body> {
    let builder = Request::builder().method(method).uri(uri);
    match body {
        Some(json) => builder
            .header("content-type", "application/json")
            .body(Body::from(json.to_string()))
            .unwrap(),
        None => builder.body(Body::empty()).unwrap(),
    }
}

/// Send a request and return the status plus parsed JSON body
/// (`Value::Null` when the response body is empty).
async fn call(app: &Router, req: Request<Body>) -> (StatusCode, Value) {
    let response = app.clone().oneshot(req).await.unwrap();
    let status = response.status();
    let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let body = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap()
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
    assert_eq!(status, StatusCode::CREATED);
    body
}

#[tokio::test]
async fn health_returns_ok() {
    let (status, body) = call(&app(), request("GET", "/health", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_book_returns_201_and_can_be_fetched() {
    let app = app();

    let (status, body) = call(
        &app,
        request(
            "POST",
            "/books",
            Some(json!({
                "title": "The Rust Book",
                "author": "Steve Klabnik",
                "year": 2019,
                "isbn": "978-1718500440"
            })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(body["id"], 1);
    assert_eq!(body["title"], "The Rust Book");
    assert_eq!(body["author"], "Steve Klabnik");
    assert_eq!(body["year"], 2019);
    assert_eq!(body["isbn"], "978-1718500440");

    let (status, body) = call(&app, request("GET", "/books/1", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "The Rust Book");
}

#[tokio::test]
async fn create_book_requires_title_and_author() {
    let app = app();

    for payload in [
        json!({ "author": "Someone" }),                    // missing title
        json!({ "title": "Something" }),                   // missing author
        json!({ "title": "  ", "author": "Someone" }),     // blank title
        json!({ "title": "Something", "author": "" }),     // blank author
    ] {
        let (status, body) = call(&app, request("POST", "/books", Some(payload))).await;
        assert_eq!(status, StatusCode::BAD_REQUEST, "payload: {body}");
        assert!(body["error"].is_string());
    }
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = app();
    create_book(&app, "Book One", "Alice").await;
    create_book(&app, "Book Two", "Bob").await;
    create_book(&app, "Book Three", "Alice").await;

    let (status, body) = call(&app, request("GET", "/books", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    let (status, body) = call(&app, request("GET", "/books?author=Alice", None)).await;
    assert_eq!(status, StatusCode::OK);
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books.iter().all(|b| b["author"] == "Alice"));

    let (status, body) = call(&app, request("GET", "/books?author=Nobody", None)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_book_replaces_fields() {
    let app = app();
    create_book(&app, "Old Title", "Old Author").await;

    let (status, body) = call(
        &app,
        request(
            "PUT",
            "/books/1",
            Some(json!({
                "title": "New Title",
                "author": "New Author",
                "year": 2024,
                "isbn": "1234567890"
            })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["id"], 1);
    assert_eq!(body["title"], "New Title");
    assert_eq!(body["author"], "New Author");
    assert_eq!(body["year"], 2024);
    assert_eq!(body["isbn"], "1234567890");

    // Update of a missing book is a 404.
    let (status, _) = call(
        &app,
        request(
            "PUT",
            "/books/999",
            Some(json!({ "title": "X", "author": "Y" })),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Update still validates required fields.
    let (status, _) = call(
        &app,
        request("PUT", "/books/1", Some(json!({ "author": "Y" }))),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn delete_book_removes_it() {
    let app = app();
    create_book(&app, "Doomed", "Author").await;

    let (status, _) = call(&app, request("DELETE", "/books/1", None)).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = call(&app, request("GET", "/books/1", None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Deleting again is a 404.
    let (status, _) = call(&app, request("DELETE", "/books/1", None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let (status, body) = call(&app(), request("GET", "/books/42", None)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body["error"].is_string());
}
