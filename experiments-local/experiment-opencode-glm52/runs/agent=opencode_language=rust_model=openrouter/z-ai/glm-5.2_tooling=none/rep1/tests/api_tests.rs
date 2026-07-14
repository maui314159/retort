use book_api::db::Db;
use book_api::error::AppError;
use book_api::models::{CreateBook, UpdateBook};
use book_api::{router, AppState};
use reqwest::StatusCode;
use serde_json::json;
use std::net::SocketAddr;
use tempfile::NamedTempFile;
use tokio::net::TcpListener;

async fn spawn() -> (SocketAddr, NamedTempFile) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let db_file = NamedTempFile::new().unwrap();
    let path = db_file.path().to_str().unwrap().to_string();
    let db = Db::open(&path).unwrap();
    let state = AppState { db };
    let app = router(state);
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    (addr, db_file)
}

fn client() -> reqwest::Client {
    reqwest::Client::builder().build().unwrap()
}

fn url(addr: SocketAddr, path: &str) -> String {
    format!("http://{addr}{path}")
}

#[tokio::test]
async fn health_check_returns_ok() {
    let (addr, _db) = spawn().await;
    let c = client();
    let resp = c.get(url(addr, "/health")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(body, json!({ "status": "ok" }));
}

#[tokio::test]
async fn create_get_list_update_delete_lifecycle() {
    let (addr, _db) = spawn().await;
    let c = client();

    // Create
    let resp = c
        .post(url(addr, "/books"))
        .json(&json!({
            "title": "The Pragmatic Programmer",
            "author": "Hunt & Thomas",
            "year": 1999,
            "isbn": "978-0201616224"
        }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let book: serde_json::Value = resp.json().await.unwrap();
    let id = book["id"].as_str().unwrap().to_string();
    assert_eq!(book["title"], "The Pragmatic Programmer");
    assert_eq!(book["author"], "Hunt & Thomas");
    assert_eq!(book["year"], 1999);

    // Get by id
    let resp = c
        .get(url(addr, &format!("/books/{id}")))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(fetched["id"], id);

    // List
    let resp = c.get(url(addr, "/books")).send().await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let list: Vec<serde_json::Value> = resp.json().await.unwrap();
    assert_eq!(list.len(), 1);

    // Filter by author
    let resp = c
        .get(url(addr, "/books"))
        .query(&[("author", "Hunt & Thomas")])
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let list: Vec<serde_json::Value> = resp.json().await.unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0]["author"], "Hunt & Thomas");

    // Filter with no match
    let resp = c
        .get(url(addr, "/books"))
        .query(&[("author", "Nobody")])
        .send()
        .await
        .unwrap();
    let list: Vec<serde_json::Value> = resp.json().await.unwrap();
    assert!(list.is_empty());

    // Update
    let resp = c
        .put(url(addr, &format!("/books/{id}")))
        .json(&json!({ "year": 2020 }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated: serde_json::Value = resp.json().await.unwrap();
    assert_eq!(updated["year"], 2020);
    assert_eq!(updated["title"], "The Pragmatic Programmer");

    // Delete
    let resp = c
        .delete(url(addr, &format!("/books/{id}")))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Get after delete -> 404
    let resp = c
        .get(url(addr, &format!("/books/{id}")))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_rejects_missing_title_and_author() {
    let (addr, _db) = spawn().await;
    let c = client();

    // Missing title
    let resp = c
        .post(url(addr, "/books"))
        .json(&json!({ "author": "Someone", "year": 2000 }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Missing author
    let resp = c
        .post(url(addr, "/books"))
        .json(&json!({ "title": "Some Title" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Blank title
    let resp = c
        .post(url(addr, "/books"))
        .json(&json!({ "title": "   ", "author": "X" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Empty update body
    let resp = c
        .post(url(addr, "/books"))
        .json(&json!({ "title": "T", "author": "A" }))
        .send()
        .await
        .unwrap();
    let book: serde_json::Value = resp.json().await.unwrap();
    let id = book["id"].as_str().unwrap().to_string();
    let resp = c
        .put(url(addr, &format!("/books/{id}")))
        .json(&json!({}))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // Update non-existent -> 404
    let resp = c
        .put(url(addr, "/books/does-not-exist"))
        .json(&json!({ "title": "New" }))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // Delete non-existent -> 404
    let resp = c
        .delete(url(addr, "/books/nope"))
        .send()
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn db_module_unit_tests() {
    let db = Db::open_in_memory().unwrap();

    let created = db
        .insert(
            "abc",
            &CreateBook {
                title: "T".into(),
                author: "A".into(),
                year: Some(2020),
                isbn: Some("i".into()),
            },
        )
        .unwrap();
    assert_eq!(created.id, "abc");
    assert_eq!(created.title, "T");

    let all = db.list(None).unwrap();
    assert_eq!(all.len(), 1);

    let filtered = db.list(Some("A")).unwrap();
    assert_eq!(filtered.len(), 1);
    let filtered_none = db.list(Some("Nope")).unwrap();
    assert!(filtered_none.is_empty());

    let updated = db
        .update(
            "abc",
            &UpdateBook {
                title: Some("T2".into()),
                author: None,
                year: Some(2021),
                isbn: None,
            },
        )
        .unwrap();
    assert_eq!(updated.title, "T2");
    assert_eq!(updated.year, Some(2021));
    assert_eq!(updated.author, "A");

    let not_found = db.get("missing").unwrap_err();
    assert!(matches!(not_found, AppError::NotFound(_)));

    db.delete("abc").unwrap();
    assert!(db.list(None).unwrap().is_empty());
}
