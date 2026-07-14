use axum::{body::Body, http::{Request, StatusCode, Method}, Router};
use book_api::create_app;
use http_body_util::BodyExt;
use serde_json::json;
use sqlx::sqlite::SqlitePoolOptions;
use tower::util::ServiceExt;

async fn setup() -> (Router, sqlx::SqlitePool) {
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect("sqlite::memory:")
        .await
        .expect("Failed to initialize in-memory db");

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT
        )
        "#
    ).execute(&pool).await.expect("Failed to create table");

    let app = create_app(pool.clone());
    (app, pool)
}

#[tokio::test]
async fn test_health_check() {
    let (app, _pool) = setup().await;
    
    let response = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    
    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    assert_eq!(&body[..], b"OK");
}

#[tokio::test]
async fn test_create_and_list_books() {
    let (app, _pool) = setup().await;
    
    let create_req = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "978-1718500440"
        }).to_string()))
        .unwrap();
        
    let response = app.clone().oneshot(create_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::CREATED, "Failed to create book: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    
    let list_req = Request::builder()
        .method(Method::GET)
        .uri("/books")
        .body(Body::empty())
        .unwrap();
        
    let response = app.oneshot(list_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK, "Failed to list books: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["title"], "The Rust Programming Language");
}

#[tokio::test]
async fn test_author_filter() {
    let (app, _pool) = setup().await;
    
    let req1 = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "title": "Book 1",
            "author": "Alice",
            "year": 2020
        }).to_string()))
        .unwrap();
    let resp1 = app.clone().oneshot(req1).await.unwrap();
    assert_eq!(resp1.status(), StatusCode::CREATED);
    
    let req2 = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "title": "Book 2",
            "author": "Bob",
            "year": 2021
        }).to_string()))
        .unwrap();
    let resp2 = app.clone().oneshot(req2).await.unwrap();
    assert_eq!(resp2.status(), StatusCode::CREATED);
    
    let filter_req = Request::builder()
        .method(Method::GET)
        .uri("/books?author=Alice")
        .body(Body::empty())
        .unwrap();
        
    let response = app.oneshot(filter_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK, "Failed to filter books: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let books: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["title"], "Book 1");
}

#[tokio::test]
async fn test_update_and_delete_book() {
    let (app, _pool) = setup().await;
    
    let create_req = Request::builder()
        .method(Method::POST)
        .uri("/books")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "title": "Old Title",
            "author": "Old Author",
            "year": 2000
        }).to_string()))
        .unwrap();
    let response = app.clone().oneshot(create_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::CREATED, "Failed to create book: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let book: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let id = book["id"].as_str().unwrap();
    
    let update_req = Request::builder()
        .method(Method::PUT)
        .uri(&format!("/books/{}", id))
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "title": "New Title"
        }).to_string()))
        .unwrap();
    let response = app.clone().oneshot(update_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK, "Failed to update book: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let updated_book: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(updated_book["title"], "New Title");
    assert_eq!(updated_book["author"], "Old Author");
    
    let delete_req = Request::builder()
        .method(Method::DELETE)
        .uri(&format!("/books/{}", id))
        .body(Body::empty())
        .unwrap();
    let response = app.clone().oneshot(delete_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::NO_CONTENT, "Failed to delete book: {:?}", response.into_body().collect().await.unwrap().to_bytes());
    
    let get_req = Request::builder()
        .method(Method::GET)
        .uri(&format!("/books/{}", id))
        .body(Body::empty())
        .unwrap();
    let response = app.oneshot(get_req).await.unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND, "Failed to get deleted book: {:?}", response.into_body().collect().await.unwrap().to_bytes());
}
