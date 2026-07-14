use axum::{
    routing::get,
    Router,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::Mutex;

mod db;
mod handlers;
mod models;

use db::{init_db, DbPool};
use handlers::{create_book, delete_book, get_book, health_check, list_books, update_book};

#[tokio::main]
async fn main() {
    let conn = init_db("books.db").expect("Failed to initialize database");
    let db_pool: DbPool = Arc::new(Mutex::new(conn));

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/books", get(list_books).post(create_book))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
        .with_state(db_pool);

    let listener = TcpListener::bind("127.0.0.1:8080").await.unwrap();
    println!("Listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::{to_bytes, Body},
        http::{Request, StatusCode},
        routing::get,
    };
    use serde_json::json;
    use tower::ServiceExt;

    fn create_test_app() -> Router {
        let conn = init_db(":memory:").expect("Failed to initialize test database");
        let db_pool = Arc::new(Mutex::new(conn));

        Router::new()
            .route("/health", get(health_check))
            .route("/books", get(list_books).post(create_book))
            .route("/books/{id}", get(get_book).put(update_book).delete(delete_book))
            .with_state(db_pool)
    }

    #[tokio::test]
    async fn test_health_check() {
        let app = create_test_app();
        let response = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["status"], "ok");
    }

    #[tokio::test]
    async fn test_create_and_get_book() {
        let app = create_test_app();

        let create_request = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                serde_json::to_string(&json!({
                    "title": "The Rust Programming Language",
                    "author": "Steve Klabnik",
                    "year": 2018,
                    "isbn": "978-1718500440"
                }))
                .unwrap(),
            ))
            .unwrap();

        let response = app.clone().oneshot(create_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);
        
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let created_book: models::Book = serde_json::from_slice(&body).unwrap();
        let book_id = created_book.id.clone();

        let get_request = Request::builder()
            .method("GET")
            .uri(format!("/books/{}", book_id))
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(get_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let fetched_book: models::Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(fetched_book.title, "The Rust Programming Language");
        assert_eq!(fetched_book.author, "Steve Klabnik");
    }

    #[tokio::test]
    async fn test_create_book_validation_fails() {
        let app = create_test_app();

        let create_request = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                serde_json::to_string(&json!({
                    "title": "",
                    "author": "   "
                }))
                .unwrap(),
            ))
            .unwrap();

        let response = app.oneshot(create_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_list_books_with_author_filter() {
        let app = create_test_app();

        let book1_req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&json!({
                "title": "Book A",
                "author": "Author One",
                "year": 2020
            })).unwrap()))
            .unwrap();
        app.clone().oneshot(book1_req).await.unwrap();

        let book2_req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&json!({
                "title": "Book B",
                "author": "Author Two",
                "year": 2021
            })).unwrap()))
            .unwrap();
        app.clone().oneshot(book2_req).await.unwrap();

        let list_request = Request::builder()
            .method("GET")
            .uri("/books?author=One")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(list_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let books: Vec<models::Book> = serde_json::from_slice(&body).unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].author, "Author One");
    }

    #[tokio::test]
    async fn test_update_and_delete_book() {
        let app = create_test_app();

        let create_request = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                serde_json::to_string(&json!({
                    "title": "Old Title",
                    "author": "Old Author",
                    "year": 2000
                })).unwrap(),
            ))
            .unwrap();

        let response = app.clone().oneshot(create_request).await.unwrap();
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let created_book: models::Book = serde_json::from_slice(&body).unwrap();
        let book_id = created_book.id;

        let update_request = Request::builder()
            .method("PUT")
            .uri(format!("/books/{}", book_id))
            .header("content-type", "application/json")
            .body(Body::from(
                serde_json::to_string(&json!({
                    "title": "New Title",
                    "year": 2023
                })).unwrap(),
            ))
            .unwrap();

        let response = app.clone().oneshot(update_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let updated_book: models::Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(updated_book.title, "New Title");
        assert_eq!(updated_book.author, "Old Author");
        assert_eq!(updated_book.year, Some(2023));

        let delete_request = Request::builder()
            .method("DELETE")
            .uri(format!("/books/{}", book_id))
            .body(Body::empty())
            .unwrap();

        let response = app.clone().oneshot(delete_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::NO_CONTENT);

        let get_request = Request::builder()
            .method("GET")
            .uri(format!("/books/{}", book_id))
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(get_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }
}