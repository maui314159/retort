use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    Router,
};
use book_api::{db, AppState};
use serde_json::{json, Value};
use sqlx::sqlite::SqlitePoolOptions;
use tower::ServiceExt;

/// Build a fresh router backed by an isolated, single-connection in-memory
/// SQLite database. Single connection is required because each in-memory
/// SQLite connection would otherwise be its own private database.
async fn build_app() -> Router {
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect("sqlite::memory:")
        .await
        .expect("connect to in-memory sqlite");
    db::init_schema(&pool)
        .await
        .expect("initialize schema");
    let state = AppState { pool };
    book_api::router(state)
}

async fn body_json(response: axum::response::Response) -> Value {
    let bytes = to_bytes(response.into_body(), 1024 * 1024)
        .await
        .expect("read body");
    serde_json::from_slice(&bytes).expect("parse json")
}

fn json_request(method: &str, uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string()))
        .expect("build request")
}

fn empty_request(method: &str, uri: &str) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .body(Body::empty())
        .expect("build request")
}

#[tokio::test]
async fn health_endpoint_returns_ok() {
    let app = build_app().await;
    let response = app
        .oneshot(empty_request("GET", "/health"))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn create_then_get_book_round_trips() {
    let app = build_app().await;

    let response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "978-0451524935"
            }),
        ))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::CREATED);
    let created = body_json(response).await;
    let id = created["id"].as_str().expect("id present").to_string();
    assert_eq!(created["title"], "1984");
    assert_eq!(created["author"], "George Orwell");
    assert_eq!(created["year"], 1949);
    assert_eq!(created["isbn"], "978-0451524935");

    let response = app
        .oneshot(empty_request("GET", &format!("/books/{}", id)))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::OK);
    let fetched = body_json(response).await;
    assert_eq!(fetched["id"], created["id"]);
    assert_eq!(fetched["title"], "1984");
    assert_eq!(fetched["author"], "George Orwell");
}

#[tokio::test]
async fn get_unknown_book_returns_404() {
    let app = build_app().await;
    let response = app
        .oneshot(empty_request("GET", "/books/does-not-exist"))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_books_supports_author_filter() {
    let app = build_app().await;

    for (title, author) in [
        ("Animal Farm", "George Orwell"),
        ("Brave New World", "Aldous Huxley"),
        ("Homage to Catalonia", "George Orwell"),
    ] {
        let response = app
            .clone()
            .oneshot(json_request(
                "POST",
                "/books",
                json!({ "title": title, "author": author }),
            ))
            .await
            .expect("create");
        assert_eq!(response.status(), StatusCode::CREATED);
    }

    // No filter — should see all three sorted by title.
    let response = app
        .clone()
        .oneshot(empty_request("GET", "/books"))
        .await
        .expect("list");
    assert_eq!(response.status(), StatusCode::OK);
    let list = body_json(response).await;
    let arr = list.as_array().expect("array");
    assert_eq!(arr.len(), 3);
    let titles: Vec<&str> = arr.iter().map(|b| b["title"].as_str().unwrap()).collect();
    assert_eq!(titles, vec!["Animal Farm", "Brave New World", "Homage to Catalonia"]);

    // Filter by author.
    let response = app
        .oneshot(empty_request("GET", "/books?author=George%20Orwell"))
        .await
        .expect("list filtered");
    assert_eq!(response.status(), StatusCode::OK);
    let filtered = body_json(response).await;
    let arr = filtered.as_array().expect("array");
    assert_eq!(arr.len(), 2);
    for book in arr {
        assert_eq!(book["author"], "George Orwell");
    }
}

#[tokio::test]
async fn create_rejects_missing_required_fields() {
    let app = build_app().await;

    // Missing author.
    let response = app
        .clone()
        .oneshot(json_request("POST", "/books", json!({ "title": "Anonymous" })))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    // Missing title.
    let response = app
        .clone()
        .oneshot(json_request("POST", "/books", json!({ "author": "Anon" })))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    // Empty title (whitespace only).
    let response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "   ", "author": "Anon" }),
        ))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    // Malformed JSON body.
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from("{not json"))
                .expect("build request"),
        )
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn update_replaces_book_fields() {
    let app = build_app().await;

    let response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Old", "author": "Alice", "year": 2000 }),
        ))
        .await
        .expect("create");
    let created = body_json(response).await;
    let id = created["id"].as_str().unwrap().to_string();

    let response = app
        .clone()
        .oneshot(json_request(
            "PUT",
            &format!("/books/{}", id),
            json!({
                "title": "New",
                "author": "Bob",
                "year": 2024,
                "isbn": "123-456"
            }),
        ))
        .await
        .expect("update");
    assert_eq!(response.status(), StatusCode::OK);
    let updated = body_json(response).await;
    assert_eq!(updated["id"], id);
    assert_eq!(updated["title"], "New");
    assert_eq!(updated["author"], "Bob");
    assert_eq!(updated["year"], 2024);
    assert_eq!(updated["isbn"], "123-456");

    // Subsequent GET sees the new values.
    let response = app
        .oneshot(empty_request("GET", &format!("/books/{}", id)))
        .await
        .expect("get");
    let fetched = body_json(response).await;
    assert_eq!(fetched["title"], "New");
    assert_eq!(fetched["author"], "Bob");
}

#[tokio::test]
async fn update_unknown_book_returns_404() {
    let app = build_app().await;
    let response = app
        .oneshot(json_request(
            "PUT",
            "/books/missing",
            json!({ "title": "X", "author": "Y" }),
        ))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_removes_book() {
    let app = build_app().await;

    let response = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({ "title": "Temp", "author": "T" }),
        ))
        .await
        .expect("create");
    let created = body_json(response).await;
    let id = created["id"].as_str().unwrap().to_string();

    let response = app
        .clone()
        .oneshot(empty_request("DELETE", &format!("/books/{}", id)))
        .await
        .expect("delete");
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    // Follow-up GET should now 404.
    let response = app
        .oneshot(empty_request("GET", &format!("/books/{}", id)))
        .await
        .expect("get");
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_unknown_book_returns_404() {
    let app = build_app().await;
    let response = app
        .oneshot(empty_request("DELETE", "/books/missing"))
        .await
        .expect("request");
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
