use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use book_collection_api::{db, routes};
use serde_json::{json, Value};
use sqlx::{SqlitePool, Row};
use tower::ServiceExt;

async fn setup_test_db() -> SqlitePool {
    let pool = db::create_pool().await.unwrap();
    sqlx::query("DELETE FROM books").execute(&pool).await.unwrap();
    pool
}

async fn create_test_app(pool: SqlitePool) -> axum::Router {
    routes::books::router(pool)
        .merge(routes::health::router())
}

#[tokio::test]
async fn test_health_endpoint() {
    let pool = setup_test_db().await;
    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let health: Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(health["status"], "ok");
}

#[tokio::test]
async fn test_create_book() {
    let pool = setup_test_db().await;
    let app = create_test_app(pool.clone()).await;

    let request_body = json!({
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(request_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["title"], "Test Book");
    assert_eq!(book["author"], "Test Author");
    assert_eq!(book["year"], 2023);
    assert_eq!(book["isbn"], "1234567890");
}

#[tokio::test]
async fn test_create_book_validation() {
    let pool = setup_test_db().await;
    let app = create_test_app(pool).await;

    let request_body = json!({
        "title": "",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(request_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_list_books() {
    let pool = setup_test_db().await;
    
    // Insert test data directly
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ('11111111-1111-1111-1111-111111111111', 'Book 1', 'Author A', 2020, '1111111111'),
               ('22222222-2222-2222-2222-222222222222', 'Book 2', 'Author B', 2021, '2222222222')
        "#,
    )
    .execute(&pool)
    .await
    .unwrap();

    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let books: Vec<Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 2);
}

#[tokio::test]
async fn test_list_books_with_author_filter() {
    let pool = setup_test_db().await;
    
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ('11111111-1111-1111-1111-111111111111', 'Book 1', 'Author A', 2020, '1111111111'),
               ('22222222-2222-2222-2222-222222222222', 'Book 2', 'Author B', 2021, '2222222222')
        "#,
    )
    .execute(&pool)
    .await
    .unwrap();

    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Author%20A")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let books: Vec<Value> = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["author"], "Author A");
}

#[tokio::test]
async fn test_get_book_by_id() {
    let pool = setup_test_db().await;
    
    let book_id = "11111111-1111-1111-1111-111111111111";
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ($1, 'Test Book', 'Test Author', 2023, '1234567890')
        "#,
    )
    .bind(book_id)
    .execute(&pool)
    .await
    .unwrap();

    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{}", book_id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["title"], "Test Book");
}

#[tokio::test]
async fn test_get_book_not_found() {
    let pool = setup_test_db().await;
    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books/11111111-1111-1111-1111-111111111111")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_book() {
    let pool = setup_test_db().await;
    
    let book_id = "11111111-1111-1111-1111-111111111111";
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ($1, 'Original Title', 'Original Author', 2020, '1111111111')
        "#,
    )
    .bind(book_id)
    .execute(&pool)
    .await
    .unwrap();

    let app = create_test_app(pool).await;

    let request_body = json!({
        "title": "Updated Title",
        "author": "Updated Author"
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", book_id))
                .header("content-type", "application/json")
                .body(Body::from(request_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let book: Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(book["title"], "Updated Title");
    assert_eq!(book["author"], "Updated Author");
    // Year and ISBN should remain unchanged
    assert_eq!(book["year"], 2020);
    assert_eq!(book["isbn"], "1111111111");
}

#[tokio::test]
async fn test_delete_book() {
    let pool = setup_test_db().await;
    
    let book_id = "11111111-1111-1111-1111-111111111111";
    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES ($1, 'Book to Delete', 'Author', 2020, '1111111111')
        "#,
    )
    .bind(book_id)
    .execute(&pool)
    .await
    .unwrap();

    let app = create_test_app(pool.clone()).await;

    // First delete
    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", book_id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    // Verify book is deleted
    let count: i64 = sqlx::query("SELECT COUNT(*) FROM books WHERE id = $1")
        .bind(book_id)
        .fetch_one(&pool)
        .await
        .unwrap()
        .get(0);
    
    assert_eq!(count, 0);
}

#[tokio::test]
async fn test_delete_book_not_found() {
    let pool = setup_test_db().await;
    let app = create_test_app(pool).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri("/books/11111111-1111-1111-1111-111111111111")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}