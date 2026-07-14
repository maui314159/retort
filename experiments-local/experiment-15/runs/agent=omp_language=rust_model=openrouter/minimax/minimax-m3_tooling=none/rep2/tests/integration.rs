//! End-to-end integration tests for the book collection API.
//!
//! Each test gets a fresh on-disk SQLite database in a temporary directory,
//! spins the real Axum router up on an OS-assigned port, and drives it
//! with `reqwest`. This exercises the full stack — router, handlers,
//! database, JSON serialization, and error mapping — without a network stub.

use std::net::SocketAddr;
use std::path::PathBuf;

use book_collection_api::{build_router, db};
use reqwest::StatusCode;
use serde_json::{json, Value};
use sqlx::sqlite::SqliteConnectOptions;
use sqlx::Pool;
use sqlx::Sqlite;
use std::str::FromStr;
use tempfile::TempDir;
use tokio::net::TcpListener;

/// A running test server bound to a random port, with its own database.
struct TestApp {
    base_url: String,
    client: reqwest::Client,
    _dir: TempDir,
    _server_handle: tokio::task::JoinHandle<()>,
}

impl TestApp {
    async fn spawn() -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        let db_path: PathBuf = dir.path().join("test.db");
        let url = format!("sqlite://{}?mode=rwc", db_path.display());

        let options = SqliteConnectOptions::from_str(&url)
            .expect("connect options")
            .create_if_missing(true)
            .foreign_keys(true);
        let pool: Pool<Sqlite> = sqlx::sqlite::SqlitePoolOptions::new()
            .max_connections(2)
            .connect_with(options)
            .await
            .expect("connect pool");
        db::run_migrations(&pool).await.expect("migrations");

        let app = build_router(pool);
        let listener = TcpListener::bind(SocketAddr::from(([127, 0, 0, 1], 0)))
            .await
            .expect("bind");
        let addr = listener.local_addr().expect("local_addr");
        let base_url = format!("http://{addr}");

        let server_handle = tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let client = reqwest::Client::builder()
            .build()
            .expect("client");

        Self {
            base_url,
            client,
            _dir: dir,
            _server_handle: server_handle,
        }
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base_url, path)
    }
}

#[tokio::test]
async fn health_endpoint_returns_ok() {
    let app = TestApp::spawn().await;

    let response = app
        .client
        .get(app.url("/health"))
        .send()
        .await
        .expect("send");

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value = response.json().await.expect("json");
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn full_crud_lifecycle() {
    let app = TestApp::spawn().await;

    // 1. List when empty.
    let response = app
        .client
        .get(app.url("/books"))
        .send()
        .await
        .expect("send");
    assert_eq!(response.status(), StatusCode::OK);
    let initial: Vec<Value> = response.json().await.expect("json");
    assert!(initial.is_empty(), "expected empty initial list");

    // 2. Create a book.
    let create = app
        .client
        .post(app.url("/books"))
        .json(&json!({
            "title": "The Left Hand of Darkness",
            "author": "Ursula K. Le Guin",
            "year": 1969,
            "isbn": "978-0-441-17271-9"
        }))
        .send()
        .await
        .expect("send");
    assert_eq!(create.status(), StatusCode::CREATED);
    let created: Value = create.json().await.expect("json");
    let id = created["id"].as_i64().expect("id");
    assert_eq!(created["title"], "The Left Hand of Darkness");
    assert_eq!(created["author"], "Ursula K. Le Guin");
    assert_eq!(created["year"], 1969);
    assert_eq!(created["isbn"], "978-0-441-17271-9");
    // 3. Get the book back.
    let get = app
        .client
        .get(app.url(&format!("/books/{id}")))
        .send()
        .await
        .expect("send");
    assert_eq!(get.status(), StatusCode::OK);

    // 4. List shows it.
    let list = app
        .client
        .get(app.url("/books"))
        .send()
        .await
        .expect("send");
    assert_eq!(list.status(), StatusCode::OK);
    let listed: Vec<Value> = list.json().await.expect("json");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0]["id"], id);

    // 5. Update it.
    let update = app
        .client
        .put(app.url(&format!("/books/{id}")))
        .json(&json!({
            "title": "The Left Hand of Darkness (Anniv. Ed.)",
            "author": "Ursula K. Le Guin",
            "year": 1969,
            "isbn": null
        }))
        .send()
        .await
        .expect("send");
    assert_eq!(update.status(), StatusCode::OK);
    let updated: Value = update.json().await.expect("json");
    assert_eq!(updated["title"], "The Left Hand of Darkness (Anniv. Ed.)");
    assert!(updated["isbn"].is_null(), "isbn should be null after update");

    // 6. Delete it.
    let delete = app
        .client
        .delete(app.url(&format!("/books/{id}")))
        .send()
        .await
        .expect("send");
    assert_eq!(delete.status(), StatusCode::NO_CONTENT);

    // 7. Now it's gone.
    let after = app
        .client
        .get(app.url(&format!("/books/{id}")))
        .send()
        .await
        .expect("send");
    assert_eq!(after.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn list_filters_by_author() {
    let app = TestApp::spawn().await;

    let books = [
        ("Dune", "Frank Herbert", 1965_i32),
        ("The Dispossessed", "Ursula K. Le Guin", 1974),
        ("A Wizard of Earthsea", "Ursula K. Le Guin", 1968),
    ];
    for (title, author, year) in books {
        let res = app
            .client
            .post(app.url("/books"))
            .json(&json!({ "title": title, "author": author, "year": year }))
            .send()
            .await
            .expect("send");
        assert_eq!(res.status(), StatusCode::CREATED, "creating {title}");
    }

    // No filter: 3 books.
    let all = app
        .client
        .get(app.url("/books"))
        .send()
        .await
        .expect("send");
    let all_json: Vec<Value> = all.json().await.expect("json");
    assert_eq!(all_json.len(), 3);

    // Filter by author: 2 books.
    let filtered = app
        .client
        .get(app.url("/books?author=Le%20Guin"))
        .send()
        .await
        .expect("send");
    assert_eq!(filtered.status(), StatusCode::OK);
    let filtered_json: Vec<Value> = filtered.json().await.expect("json");
    assert_eq!(filtered_json.len(), 2);
    for book in &filtered_json {
        assert!(book["author"]
            .as_str()
            .unwrap()
            .to_lowercase()
            .contains("le guin"));
    }

    // Filter with no matches.
    let none = app
        .client
        .get(app.url("/books?author=Nobody"))
        .send()
        .await
        .expect("send");
    let none_json: Vec<Value> = none.json().await.expect("json");
    assert!(none_json.is_empty());
}

#[tokio::test]
async fn missing_required_fields_returns_400() {
    let app = TestApp::spawn().await;

    // Missing title.
    let no_title = app
        .client
        .post(app.url("/books"))
        .json(&json!({ "author": "Anon" }))
        .send()
        .await
        .expect("send");
    assert_eq!(no_title.status(), StatusCode::BAD_REQUEST);
    let body: Value = no_title.json().await.expect("json");
    assert_eq!(body["error"]["code"], "validation_error");

    // Missing author.
    let no_author = app
        .client
        .post(app.url("/books"))
        .json(&json!({ "title": "Anonymous" }))
        .send()
        .await
        .expect("send");
    assert_eq!(no_author.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn unknown_id_returns_404() {
    let app = TestApp::spawn().await;

    let get = app
        .client
        .get(app.url("/books/9999"))
        .send()
        .await
        .expect("send");
    assert_eq!(get.status(), StatusCode::NOT_FOUND);

    let update = app
        .client
        .put(app.url("/books/9999"))
        .json(&json!({ "title": "x", "author": "y" }))
        .send()
        .await
        .expect("send");
    assert_eq!(update.status(), StatusCode::NOT_FOUND);

    let delete = app
        .client
        .delete(app.url("/books/9999"))
        .send()
        .await
        .expect("send");
    assert_eq!(delete.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn invalid_id_path_returns_400() {
    let app = TestApp::spawn().await;

    let res = app
        .client
        .get(app.url("/books/not-a-number"))
        .send()
        .await
        .expect("send");
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}
