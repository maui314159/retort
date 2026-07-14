use std::sync::Arc;

mod server {
    include!("../src/main.rs");
}

use server::{app, ApiError, Book, BookInput};
use tower::ServiceExt;

fn in_memory_db() -> Arc<std::sync::Mutex<rusqlite::Connection>> {
    let conn = rusqlite::Connection::open_in_memory().unwrap();
    server::init_db(&conn).unwrap();
    Arc::new(std::sync::Mutex::new(conn))
}

#[tokio::test]
async fn create_and_get_book() {
    let db = in_memory_db();
    let app = app(db);

    let input = BookInput {
        title: "The Hobbit".into(),
        author: "J.R.R. Tolkien".into(),
        year: Some(1937),
        isbn: Some("9780261103283".into()),
    };
    let resp = app
        .clone()
        .oneshot(
            axum::http::Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(axum::body::Body::from(serde_json::to_vec(&input).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::CREATED);
    let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let book: Book = serde_json::from_slice(&body).unwrap();
    assert_eq!(book.title, "The Hobbit");
    assert_eq!(book.id, 1);

    // GET it back
    let app2 = app.clone();
    let get_resp = app2
        .oneshot(
            axum::http::Request::builder()
                .method("GET")
                .uri("/books/1")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(get_resp.status(), axum::http::StatusCode::OK);
}

#[tokio::test]
async fn create_rejects_empty_title() {
    let db = in_memory_db();
    let app = app(db);
    let input = serde_json::json!({"title": "", "author": "X"});
    let resp = app
        .oneshot(
            axum::http::Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(axum::body::Body::from(input.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter_and_delete() {
    let db = in_memory_db();
    let app = app(db.clone());

    // seed two books
    server::insert_book(
        &db,
        &BookInput {
            title: "A".into(),
            author: "Alice".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();
    server::insert_book(
        &db,
        &BookInput {
            title: "B".into(),
            author: "Bob".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();

    // filter by author=Bob
    let resp = app
        .clone()
        .oneshot(
            axum::http::Request::builder()
                .method("GET")
                .uri("/books?author=Bob")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::OK);
    let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let books: Vec<Book> = serde_json::from_slice(&body).unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0].author, "Bob");

    // delete book 1
    let resp = app
        .clone()
        .oneshot(
            axum::http::Request::builder()
                .method("DELETE")
                .uri("/books/1")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::NO_CONTENT);

    // now GET /books/1 -> 404
    let resp = app
        .oneshot(
            axum::http::Request::builder()
                .method("GET")
                .uri("/books/1")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_ok() {
    let db = in_memory_db();
    let app = app(db);
    let resp = app
        .oneshot(
            axum::http::Request::builder()
                .method("GET")
                .uri("/health")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::OK);
}

#[tokio::test]
async fn update_book() {
    let db = in_memory_db();
    let app = app(db.clone());
    server::insert_book(
        &db,
        &BookInput {
            title: "Old".into(),
            author: "Auth".into(),
            year: Some(2000),
            isbn: None,
        },
    )
    .unwrap();

    let update = serde_json::json!({"title": "New"});
    let resp = app
        .oneshot(
            axum::http::Request::builder()
                .method("PUT")
                .uri("/books/1")
                .header("content-type", "application/json")
                .body(axum::body::Body::from(update.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), axum::http::StatusCode::OK);
    let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let book: Book = serde_json::from_slice(&body).unwrap();
    assert_eq!(book.title, "New");
    assert_eq!(book.author, "Auth");
}

// ensure ApiError variants are still considered used
fn _silence(_e: ApiError) {}
