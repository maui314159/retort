use books_api::{db, handlers};
use reqwest::StatusCode;
use serde_json::json;
use sqlx::sqlite::SqlitePoolOptions;
use tokio::net::TcpListener;

/// Build the application with a fresh in-memory SQLite database and bind it to
/// an ephemeral local port. Returns the base URL and the spawned server handle.
async fn setup() -> (String, tokio::task::JoinHandle<()>) {
    // A single long-lived connection is required for `:memory:` so that every
    // query sees the same in-memory database.
    let pool = SqlitePoolOptions::new()
        .min_connections(1)
        .max_connections(1)
        .connect("sqlite::memory:")
        .await
        .expect("connect in-memory sqlite");
    db::init(&pool).await.expect("init schema");

    let state = handlers::AppState { pool };
    let app = handlers::router(state);

    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("local addr");
    let handle = tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    (format!("http://{addr}"), handle)
}

#[tokio::test]
async fn health_check_returns_ok() {
    let (base, _handle) = setup().await;
    let res = reqwest::get(format!("{base}/health")).await.unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let body: serde_json::Value = res.json().await.unwrap();
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_get_list_and_delete_book() {
    let (base, _handle) = setup().await;
    let client = reqwest::Client::new();

    // Create a book -> 201
    let resp = client
        .post(format!("{base}/books"))
        .json(&json!({
            "title": "The Rust Book",
            "author": "Klabnik",
            "year": 2024,
            "isbn": "978-0000000000"
        }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created: serde_json::Value = resp.json().await.unwrap();
    let id = created["id"].as_i64().expect("id present");
    assert_eq!(created["title"], "The Rust Book");
    assert_eq!(created["author"], "Klabnik");
    assert_eq!(created["year"], 2024);

    // GET by id -> 200
    let resp = client.get(format!("{base}/books/{id}")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(body["id"], id);

    // GET by unknown id -> 404
    let resp = client.get(format!("{base}/books/9999")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // List returns 1 book
    let resp = client.get(format!("{base}/books")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let arr: Vec<serde_json::Value> = resp.json().await.unwrap();
    assert_eq!(arr.len(), 1);

    // Update book -> 200
    let resp = client
        .put(format!("{base}/books/{id}"))
        .json(&json!({
            "title": "The Rust Book 2nd ed",
            "author": "Klabnik & Nichols",
            "year": 2025,
            "isbn": "978-1111111111"
        }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(body["title"], "The Rust Book 2nd ed");
    assert_eq!(body["year"], 2025);

    // Delete -> 204, then GET -> 404
    let resp = client.delete(format!("{base}/books/{id}")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);
    let resp = client.get(format!("{base}/books/{id}")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // Delete again -> 404
    let resp = client.delete(format!("{base}/books/{id}")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn create_rejects_missing_and_empty_required_fields() {
    let (base, _handle) = setup().await;
    let client = reqwest::Client::new();

    // Missing title entirely
    let resp = client
        .post(format!("{base}/books"))
        .json(&json!({ "author": "Someone", "year": 2000 }))
        .send()
        .await
        .unwrap();
    let status = resp.status();
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let body: serde_json::Value = resp.json().await.unwrap();
    assert!(body["error"].as_str().unwrap().contains("title"));

    // Empty title
    let resp = client
        .post(format!("{base}/books"))
        .json(&json!({ "title": "   ", "author": "Someone" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Missing author
    let resp = client
        .post(format!("{base}/books"))
        .json(&json!({ "title": "Title" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Valid request still succeeds after the rejections
    let resp = client
        .post(format!("{base}/books"))
        .json(&json!({ "title": "OK", "author": "A" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let body: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(body["title"], "OK");
    assert_eq!(body["author"], "A");
    assert!(body["year"].is_null());
    assert!(body["isbn"].is_null());
}

#[tokio::test]
async fn list_supports_author_filter() {
    let (base, _handle) = setup().await;
    let client = reqwest::Client::new();

    // Seed three books, two by "Asimov" and one by "Clarke".
    for (title, author) in [
        ("Foundation", "Asimov"),
        ("I, Robot", "Asimov"),
        ("2001", "Clarke"),
    ] {
        let resp = client
            .post(format!("{base}/books"))
            .json(&json!({ "title": title, "author": author }))
            .send()
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    // No filter -> 3 books
    let arr: Vec<serde_json::Value> =
        client.get(format!("{base}/books")).send().await.unwrap().json().await.unwrap();
    assert_eq!(arr.len(), 3);

    // Filter by author=Asimov -> 2 books, all authored by Asimov
    let arr: Vec<serde_json::Value> = client
        .get(format!("{base}/books?author=Asimov"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(arr.len(), 2);
    assert!(arr.iter().all(|b| b["author"] == "Asimov"));

    // Filter by an author with no matches -> empty array, still 200
    let arr: Vec<serde_json::Value> = client
        .get(format!("{base}/books?author=Nobody"))
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    assert_eq!(arr.len(), 0);
}
