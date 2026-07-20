//! End-to-end tests: the real router is exercised in-process against an
//! in-memory SQLite database, so no TCP port is required.

use std::sync::Arc;

use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use book_collection_api::{build_router, init_db, AppState};
use serde_json::{json, Value};
use tower::ServiceExt; // for `oneshot`

fn app() -> Router {
    let conn = init_db(":memory:").unwrap();
    build_router(Arc::new(AppState::new(conn)))
}

/// Send a request with an optional raw string body and return (status, json body).
async fn request_raw(
    app: &Router,
    method: &str,
    uri: &str,
    raw_body: Option<String>,
) -> (StatusCode, Value) {
    let mut builder = Request::builder().method(method).uri(uri);
    let body = match raw_body {
        Some(payload) => {
            builder = builder.header("content-type", "application/json");
            Body::from(payload)
        }
        None => Body::empty(),
    };
    let response = app
        .clone()
        .oneshot(builder.body(body).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        // Our own error responses are JSON; axum's extractor rejections are
        // plain text, which we surface as a JSON string for simplicity.
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| Value::String(String::from_utf8_lossy(&bytes).into_owned()))
    };
    (status, json)
}

/// Send a request with an optional JSON body.
async fn request(app: &Router, method: &str, uri: &str, body: Option<Value>) -> (StatusCode, Value) {
    request_raw(app, method, uri, body.map(|v| v.to_string())).await
}

#[tokio::test]
async fn health_check() {
    let (status, body) = request(&app(), "GET", "/health", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_then_get_book() {
    let app = app();

    let (status, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "9780441172719"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let id = created["id"].as_i64().unwrap();
    assert_eq!(created["title"], "Dune");

    let (status, fetched) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(fetched["author"], "Frank Herbert");
    assert_eq!(fetched["year"], 1965);
    assert_eq!(fetched["isbn"], "9780441172719");
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = app();
    for (title, author) in [
        ("Dune", "Frank Herbert"),
        ("Dune Messiah", "Frank Herbert"),
        ("Neuromancer", "William Gibson"),
    ] {
        let (status, _) = request(
            &app,
            "POST",
            "/books",
            Some(json!({ "title": title, "author": author })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, all) = request(&app, "GET", "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(all.as_array().unwrap().len(), 3);

    let (status, filtered) = request(&app, "GET", "/books?author=Frank%20Herbert", None).await;
    assert_eq!(status, StatusCode::OK);
    let filtered = filtered.as_array().unwrap();
    assert_eq!(filtered.len(), 2);
    assert!(filtered.iter().all(|b| b["author"] == "Frank Herbert"));

    // Author with no books -> 200 with empty array.
    let (status, empty) = request(&app, "GET", "/books?author=Nobody", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(empty.as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn update_book() {
    let app = app();
    let (_, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Old Title", "author": "Author" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, updated) = request(
        &app,
        "PUT",
        &format!("/books/{id}"),
        Some(json!({ "title": "New Title", "author": "Author", "year": 2024 })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["year"], 2024);

    // The change is persisted.
    let (_, fetched) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(fetched["title"], "New Title");

    // Updating a nonexistent book returns 404.
    let (status, _) = request(
        &app,
        "PUT",
        "/books/999",
        Some(json!({ "title": "X", "author": "Y" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_book() {
    let app = app();
    let (_, created) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Bye", "author": "Someone" })),
    )
    .await;
    let id = created["id"].as_i64().unwrap();

    let (status, _) = request(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    let (status, _) = request(&app, "GET", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    // Deleting again is a 404.
    let (status, _) = request(&app, "DELETE", &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_errors() {
    let app = app();

    // Blank title -> 400 with JSON error body.
    let (status, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "   ", "author": "Author" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "title is required");

    // Blank author -> 400.
    let (status, body) = request(
        &app,
        "POST",
        "/books",
        Some(json!({ "title": "Title", "author": "" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert_eq!(body["error"], "author is required");

    // Missing required field -> 422 (JSON extractor rejection).
    let (status, _) = request(&app, "POST", "/books", Some(json!({ "title": "T" }))).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);

    // Malformed JSON -> 400.
    let (status, _) = request_raw(&app, "POST", "/books", Some("{not json".to_string())).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn get_nonexistent_book() {
    let (status, body) = request(&app(), "GET", "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["error"], "book 999 not found");
}
