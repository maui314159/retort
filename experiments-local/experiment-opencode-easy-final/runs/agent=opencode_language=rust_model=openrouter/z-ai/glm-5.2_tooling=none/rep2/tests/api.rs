use books_api::{app, make_pool};
use reqwest::StatusCode;
use serde_json::{json, Value};

async fn spawn() -> String {
    let pool = make_pool("sqlite::memory:").await.unwrap();
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let router = app(pool);
    tokio::spawn(async move {
        let _ = axum::serve(listener, router).await;
    });
    format!("http://{}", addr)
}

#[tokio::test]
async fn create_and_get_book() {
    let base = spawn().await;
    let client = reqwest::Client::new();

    let resp = client
        .post(format!("{}/books", base))
        .json(&json!({
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "9780261103283"
        }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let body: Value = resp.json().await.unwrap();
    let id = body["id"].as_i64().unwrap();

    let resp = client
        .get(format!("{}/books/{}", base, id))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: Value = resp.json().await.unwrap();
    assert_eq!(body["title"], "The Hobbit");
    assert_eq!(body["author"], "J.R.R. Tolkien");
    assert_eq!(body["year"], 1937);
}

#[tokio::test]
async fn validation_rejects_missing_title() {
    let base = spawn().await;
    let client = reqwest::Client::new();

    let resp = client
        .post(format!("{}/books", base))
        .json(&json!({"title": "", "author": "Someone"}))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter() {
    let base = spawn().await;
    let client = reqwest::Client::new();

    client
        .post(format!("{}/books", base))
        .json(&json!({"title": "A", "author": "Alice"}))
        .send()
        .await
        .unwrap();
    client
        .post(format!("{}/books", base))
        .json(&json!({"title": "B", "author": "Bob"}))
        .send()
        .await
        .unwrap();

    let resp = client
        .get(format!("{}/books?author=Alice", base))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: Vec<Value> = resp.json().await.unwrap();
    assert_eq!(body.len(), 1);
    assert_eq!(body[0]["author"], "Alice");
}

#[tokio::test]
async fn update_and_delete() {
    let base = spawn().await;
    let client = reqwest::Client::new();

    let resp = client
        .post(format!("{}/books", base))
        .json(&json!({"title": "Old", "author": "Auth"}))
        .send()
        .await
        .unwrap();
    let body: Value = resp.json().await.unwrap();
    let id = body["id"].as_i64().unwrap();

    let resp = client
        .put(format!("{}/books/{}", base, id))
        .json(&json!({"title": "New"}))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: Value = resp.json().await.unwrap();
    assert_eq!(body["title"], "New");
    assert_eq!(body["author"], "Auth");

    let resp = client
        .delete(format!("{}/books/{}", base, id))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let resp = client
        .get(format!("{}/books/{}", base, id))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_ok() {
    let base = spawn().await;
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{}/health", base))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = resp.text().await.unwrap();
    assert_eq!(body, "ok");
}
