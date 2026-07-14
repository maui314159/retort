//! Integration tests for the books API.
//!
//! Each test gets a fresh in-memory SQLite database, so tests can be
//! safely run in parallel.

use std::sync::atomic::{AtomicU64, Ordering};

use axum::body::{to_bytes, Body};
use axum::http::{header, Method, Request, StatusCode};
use books_api::{build_app, db};
use serde_json::{json, Value};
use tower::ServiceExt;

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// Build an isolated in-memory database and return a router ready to be
/// driven via `oneshot`. The shared-cache name is unique per test so
/// parallel tests cannot see each other's data.
async fn fresh_app() -> axum::Router {
    let id = COUNTER.fetch_add(1, Ordering::SeqCst);
    let url = format!(
        "sqlite:file:books-test-{}-{}?mode=memory&cache=shared",
        std::process::id(),
        id
    );
    let pool = db::init_pool(&url).await.expect("init pool");
    build_app(pool)
}

/// Send a request and return (status, body-as-string).
async fn send(
    app: axum::Router,
    method: Method,
    uri: &str,
    json_body: Option<&Value>,
) -> (StatusCode, String) {
    let body = match json_body {
        Some(v) => Body::from(v.to_string()),
        None => Body::empty(),
    };

    let mut builder = Request::builder().method(method).uri(uri);
    if json_body.is_some() {
        builder = builder.header(header::CONTENT_TYPE, "application/json");
    }
    let request = builder.body(body).expect("build request");

    let response = app.oneshot(request).await.expect("response");
    let status = response.status();
    let bytes = to_bytes(response.into_body(), 1024 * 1024)
        .await
        .expect("body bytes");
    let text = String::from_utf8(bytes.to_vec()).unwrap_or_default();
    (status, text)
}

fn parse(text: &str) -> Value {
    serde_json::from_str(text).unwrap_or(Value::Null)
}

#[tokio::test]
async fn health_endpoint_returns_ok() {
    let app = fresh_app().await;

    let (status, body) = send(app, Method::GET, "/health", None).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(parse(&body), json!({ "status": "ok" }));
}

#[tokio::test]
async fn crud_lifecycle_round_trip() {
    let app = fresh_app().await;

    // CREATE — 201, returns the created book with id
    let (status, body) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(&json!({
            "title": "The Pragmatic Programmer",
            "author": "Andy Hunt",
            "year": 1999,
            "isbn": "978-0201616224"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "create body: {body}");
    let created = parse(&body);
    assert_eq!(created["title"], "The Pragmatic Programmer");
    assert_eq!(created["author"], "Andy Hunt");
    assert_eq!(created["year"], 1999);
    assert_eq!(created["isbn"], "978-0201616224");
    let id = created["id"].as_i64().expect("id is i64");

    // READ — 200, returns the same book
    let (status, body) = send(app.clone(), Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(parse(&body)["id"], id);

    // UPDATE — 200, fields changed
    let (status, body) = send(
        app.clone(),
        Method::PUT,
        &format!("/books/{id}"),
        Some(&json!({
            "title": "The Pragmatic Programmer, 20th Anniversary",
            "author": "Andy Hunt",
            "year": 2019,
            "isbn": "978-0135957059"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::OK, "update body: {body}");
    let updated = parse(&body);
    assert_eq!(updated["title"], "The Pragmatic Programmer, 20th Anniversary");
    assert_eq!(updated["year"], 2019);
    assert_eq!(updated["isbn"], "978-0135957059");

    // DELETE — 204
    let (status, body) = send(app.clone(), Method::DELETE, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NO_CONTENT);
    assert!(body.is_empty());

    // GET after delete — 404
    let (status, body) = send(app, Method::GET, &format!("/books/{id}"), None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    let parsed = parse(&body);
    assert_eq!(parsed["error"], "book not found");
}

#[tokio::test]
async fn list_books_and_filter_by_author() {
    let app = fresh_app().await;

    // Empty list
    let (status, body) = send(app.clone(), Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(parse(&body), json!([]));

    // Create three books
    for (title, author, year) in [
        ("Refactoring", "Martin Fowler", 1999_i32),
        ("Patterns of Enterprise Application Architecture", "Martin Fowler", 2002),
        ("Clean Code", "Robert C. Martin", 2008),
    ] {
        let (status, body) = send(
            app.clone(),
            Method::POST,
            "/books",
            Some(&json!({ "title": title, "author": author, "year": year })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED, "create body: {body}");
    }

    // List all — three results
    let (status, body) = send(app.clone(), Method::GET, "/books", None).await;
    assert_eq!(status, StatusCode::OK);
    let all = parse(&body).as_array().cloned().unwrap_or_default();
    assert_eq!(all.len(), 3);

    // Filter by author (case-insensitive exact match)
    let (status, body) = send(
        app.clone(),
        Method::GET,
        "/books?author=martin%20fowler",
        None,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let filtered = parse(&body).as_array().cloned().unwrap_or_default();
    assert_eq!(filtered.len(), 2);
    for book in &filtered {
        assert_eq!(book["author"], "Martin Fowler");
    }

    // Empty author filter is treated as "no filter"
    let (status, body) = send(app, Method::GET, "/books?author=", None).await;
    assert_eq!(status, StatusCode::OK);
    let all_again = parse(&body).as_array().cloned().unwrap_or_default();
    assert_eq!(all_again.len(), 3);
}

#[tokio::test]
async fn validation_rejects_missing_required_fields() {
    let app = fresh_app().await;

    // Missing title
    let (status, body) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(&json!({ "author": "Anonymous" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let parsed = parse(&body);
    assert!(
        parsed["error"].as_str().unwrap().contains("title"),
        "expected title-required error, got {parsed}"
    );

    // Missing author
    let (status, body) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(&json!({ "title": "Untitled" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let parsed = parse(&body);
    assert!(
        parsed["error"].as_str().unwrap().contains("author"),
        "expected author-required error, got {parsed}"
    );

    // Whitespace-only title
    let (status, _body) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(&json!({ "title": "   ", "author": "Anonymous" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // Same checks on PUT — title and author are also required for updates.
    let (status, _) = send(
        app.clone(),
        Method::POST,
        "/books",
        Some(&json!({ "title": "Seeded", "author": "Seed" })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);

    let (status, body) = send(
        app,
        Method::PUT,
        "/books/1",
        Some(&json!({ "title": "Updated" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(parse(&body)["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn not_found_for_missing_resources() {
    let app = fresh_app().await;

    let (status, _) = send(app.clone(), Method::GET, "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(
        app.clone(),
        Method::PUT,
        "/books/999",
        Some(&json!({ "title": "x", "author": "y" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, _) = send(app, Method::DELETE, "/books/999", None).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn invalid_id_returns_400() {
    let app = fresh_app().await;

    let (status, _) = send(app, Method::GET, "/books/not-a-number", None).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}
