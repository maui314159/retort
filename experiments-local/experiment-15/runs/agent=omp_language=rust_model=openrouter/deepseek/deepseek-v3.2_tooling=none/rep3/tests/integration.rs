use book_api::handlers;
use axum::{Router, routing::{get, post, put, delete}};
use sqlx::SqlitePool;
use tokio::net::TcpListener;

async fn setup_app() -> (Router, String) {
    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    sqlx::migrate!("./migrations").run(&pool).await.unwrap();
    
    let app = Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book))
        .route("/books", get(handlers::list_books))
        .route("/books/:id", get(handlers::get_book))
        .route("/books/:id", put(handlers::update_book))
        .route("/books/:id", delete(handlers::delete_book))
        .with_state(pool);

    // Start server on random port
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let port = addr.port();
    
    let app_clone = app.clone();
    tokio::spawn(async move {
        axum::serve(listener, app_clone).await.unwrap();
    });
    
    (app, format!("http://127.0.0.1:{}", port))
}

#[tokio::test]
async fn test_health_endpoint() {
    let (_, base_url) = setup_app().await;
    
    let client = reqwest::Client::new();
    let response = client.get(&format!("{}/health", base_url))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let body: serde_json::Value = response.json().await.unwrap();
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn test_create_and_list_books() {
    let (_, base_url) = setup_app().await;
    let client = reqwest::Client::new();
    
    // Create a book
    let book_data = serde_json::json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik and Carol Nichols",
        "year": 2018,
        "isbn": "978-1593278281"
    });
    
    let response = client.post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 201);
    let created_book: serde_json::Value = response.json().await.unwrap();
    assert_eq!(created_book["title"], "The Rust Programming Language");
    assert_eq!(created_book["author"], "Steve Klabnik and Carol Nichols");
    assert_eq!(created_book["year"], 2018);
    assert_eq!(created_book["isbn"], "978-1593278281");
    
    // List books
    let response = client.get(&format!("{}/books", base_url))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let books: Vec<serde_json::Value> = response.json().await.unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["title"], "The Rust Programming Language");
}

#[tokio::test]
async fn test_create_book_validation() {
    let (_, base_url) = setup_app().await;
    let client = reqwest::Client::new();
    
    // Missing title
    let invalid_data = serde_json::json!({
        "author": "Test Author"
    });
    
    let response = client.post(&format!("{}/books", base_url))
        .json(&invalid_data)
        .send()
        .await
        .unwrap();
    
    assert!(response.status() == 400 || response.status() == 422);
    
    // Missing author
    let invalid_data2 = serde_json::json!({
        "title": "Test Book"
    });
    
    let response = client.post(&format!("{}/books", base_url))
        .json(&invalid_data2)
        .send()
        .await
        .unwrap();
    
    assert!(response.status() == 400 || response.status() == 422);
}

#[tokio::test]
async fn test_get_update_delete_book() {
    let (_, base_url) = setup_app().await;
    let client = reqwest::Client::new();
    
    // Create a book
    let book_data = serde_json::json!({
        "title": "Original Title",
        "author": "Original Author",
        "year": 2020,
        "isbn": "1111111111"
    });
    
    let response = client.post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 201);
    let created_book: serde_json::Value = response.json().await.unwrap();
    let book_id = created_book["id"].as_str().unwrap();
    
    // Get the book
    let response = client.get(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let fetched_book: serde_json::Value = response.json().await.unwrap();
    assert_eq!(fetched_book["title"], "Original Title");
    
    // Update the book
    let update_data = serde_json::json!({
        "title": "Updated Title",
        "author": "Updated Author"
    });
    
    let response = client.put(&format!("{}/books/{}", base_url, book_id))
        .json(&update_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let updated_book: serde_json::Value = response.json().await.unwrap();
    assert_eq!(updated_book["title"], "Updated Title");
    assert_eq!(updated_book["author"], "Updated Author");
    
    // Delete the book
    let response = client.delete(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 204);
    
    // Verify book is deleted
    let response = client.get(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 404);
}

#[tokio::test]
async fn test_list_books_with_author_filter() {
    let (_, base_url) = setup_app().await;
    let client = reqwest::Client::new();
    
    // Create two books with different authors
    let book1 = serde_json::json!({
        "title": "Book 1",
        "author": "Author A",
        "year": 2020
    });
    
    let book2 = serde_json::json!({
        "title": "Book 2",
        "author": "Author B",
        "year": 2021
    });
    
    client.post(&format!("{}/books", base_url))
        .json(&book1)
        .send()
        .await
        .unwrap();
    
    client.post(&format!("{}/books", base_url))
        .json(&book2)
        .send()
        .await
        .unwrap();
    
    // List all books
    let response = client.get(&format!("{}/books", base_url))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let books: Vec<serde_json::Value> = response.json().await.unwrap();
    assert_eq!(books.len(), 2);
    
    // List books by author
    let response = client.get(&format!("{}/books?author=Author%20A", base_url))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let books: Vec<serde_json::Value> = response.json().await.unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["author"], "Author A");
}