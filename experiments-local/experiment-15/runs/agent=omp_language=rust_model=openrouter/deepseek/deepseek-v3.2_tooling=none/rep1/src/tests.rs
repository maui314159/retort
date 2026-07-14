#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        database::create_test_pool,
        models::{Book, CreateBook, UpdateBook},
    };
    use axum::{
        body::Body,
        http::{Method, Request, StatusCode},
        Router,
    };
    use tower::ServiceExt;

    async fn setup_test_app() -> Router {
        let pool = create_test_pool().await.unwrap();
        crate::handlers::create_router(pool)
    }

    #[tokio::test]
    async fn test_create_book() {
        let app = setup_test_app().await;

        let book_data = CreateBook {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        let book: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(book.title, "Test Book");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2023);
        assert_eq!(book.isbn, "1234567890");
    }

    #[tokio::test]
    async fn test_create_book_validation() {
        let app = setup_test_app().await;

        // Missing title
        let book_data = CreateBook {
            title: "".to_string(),
            author: "Test Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);

        // Missing author
        let book_data = CreateBook {
            title: "Test Book".to_string(),
            author: "".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);

        // Invalid year
        let book_data = CreateBook {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 99,
            isbn: "1234567890".to_string(),
        };

        let request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_get_book() {
        let app = setup_test_app().await;

        // First create a book
        let book_data = CreateBook {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let create_request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let create_response = app.clone().oneshot(create_request).await.unwrap();
        let body = hyper::body::to_bytes(create_response.into_body()).await.unwrap();
        let created_book: Book = serde_json::from_slice(&body).unwrap();

        // Now get the book
        let get_request = Request::builder()
            .method(Method::GET)
            .uri(format!("/books/{}", created_book.id))
            .body(Body::empty())
            .unwrap();

        let get_response = app.clone().oneshot(get_request).await.unwrap();
        assert_eq!(get_response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(get_response.into_body()).await.unwrap();
        let book: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(book.id, created_book.id);
    }

    #[tokio::test]
    async fn test_update_book() {
        let app = setup_test_app().await;

        // Create a book
        let book_data = CreateBook {
            title: "Original Title".to_string(),
            author: "Original Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let create_request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let create_response = app.clone().oneshot(create_request).await.unwrap();
        let body = hyper::body::to_bytes(create_response.into_body()).await.unwrap();
        let created_book: Book = serde_json::from_slice(&body).unwrap();

        // Update the book
        let update_data = UpdateBook {
            title: Some("Updated Title".to_string()),
            author: Some("Updated Author".to_string()),
            year: Some(2024),
            isbn: Some("0987654321".to_string()),
        };

        let update_request = Request::builder()
            .method(Method::PUT)
            .uri(format!("/books/{}", created_book.id))
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&update_data).unwrap()))
            .unwrap();

        let update_response = app.clone().oneshot(update_request).await.unwrap();
        assert_eq!(update_response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(update_response.into_body()).await.unwrap();
        let updated_book: Book = serde_json::from_slice(&body).unwrap();
        assert_eq!(updated_book.title, "Updated Title");
        assert_eq!(updated_book.author, "Updated Author");
        assert_eq!(updated_book.year, 2024);
        assert_eq!(updated_book.isbn, "0987654321");
    }

    #[tokio::test]
    async fn test_delete_book() {
        let app = setup_test_app().await;

        // Create a book
        let book_data = CreateBook {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        let create_request = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book_data).unwrap()))
            .unwrap();

        let create_response = app.clone().oneshot(create_request).await.unwrap();
        let body = hyper::body::to_bytes(create_response.into_body()).await.unwrap();
        let created_book: Book = serde_json::from_slice(&body).unwrap();

        // Delete the book
        let delete_request = Request::builder()
            .method(Method::DELETE)
            .uri(format!("/books/{}", created_book.id))
            .body(Body::empty())
            .unwrap();

        let delete_response = app.clone().oneshot(delete_request).await.unwrap();
        assert_eq!(delete_response.status(), StatusCode::NO_CONTENT);

        // Try to get the deleted book
        let get_request = Request::builder()
            .method(Method::GET)
            .uri(format!("/books/{}", created_book.id))
            .body(Body::empty())
            .unwrap();

        let get_response = app.clone().oneshot(get_request).await.unwrap();
        assert_eq!(get_response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_list_books_with_filter() {
        let app = setup_test_app().await;

        // Create two books with different authors
        let book1_data = CreateBook {
            title: "Book 1".to_string(),
            author: "Author A".to_string(),
            year: 2023,
            isbn: "1111111111".to_string(),
        };

        let book2_data = CreateBook {
            title: "Book 2".to_string(),
            author: "Author B".to_string(),
            year: 2024,
            isbn: "2222222222".to_string(),
        };

        // Create first book
        let request1 = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book1_data).unwrap()))
            .unwrap();

        app.clone().oneshot(request1).await.unwrap();

        // Create second book
        let request2 = Request::builder()
            .method(Method::POST)
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_string(&book2_data).unwrap()))
            .unwrap();

        app.clone().oneshot(request2).await.unwrap();

        // List all books
        let list_request = Request::builder()
            .method(Method::GET)
            .uri("/books")
            .body(Body::empty())
            .unwrap();

        let list_response = app.clone().oneshot(list_request).await.unwrap();
        assert_eq!(list_response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(list_response.into_body()).await.unwrap();
        let books: Vec<Book> = serde_json::from_slice(&body).unwrap();
        assert_eq!(books.len(), 2);

        // List books filtered by author
        let filtered_request = Request::builder()
            .method(Method::GET)
            .uri("/books?author=Author%20A")
            .body(Body::empty())
            .unwrap();

        let filtered_response = app.clone().oneshot(filtered_request).await.unwrap();
        assert_eq!(filtered_response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(filtered_response.into_body()).await.unwrap();
        let books: Vec<Book> = serde_json::from_slice(&body).unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].author, "Author A");
    }

    #[tokio::test]
    async fn test_health_endpoint() {
        let app = setup_test_app().await;

        let request = Request::builder()
            .method(Method::GET)
            .uri("/health")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        assert_eq!(body, "OK");
    }
}