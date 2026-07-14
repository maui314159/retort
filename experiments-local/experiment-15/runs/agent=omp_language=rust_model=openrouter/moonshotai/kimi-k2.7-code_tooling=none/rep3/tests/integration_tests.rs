use axum::body::Body;
use axum::http::{self, Request, StatusCode};
use book_api::create_app;
use serde_json::{json, Value};
use tower::ServiceExt;

fn json_request(method: http::Method, uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header(http::header::CONTENT_TYPE, "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let app = create_app(":memory:").unwrap();
    let response = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}

async fn body_json(response: axum::response::Response) -> Value {
    let bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn full_crud_lifecycle() {
    let app = create_app(":memory:").unwrap();

    // Create
    let create = json_request(
        http::Method::POST,
        "/books",
        json!({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}),
    );
    let response = app.clone().oneshot(create).await.unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    let book: Value = body_json(response).await;
    let id = book["id"].as_str().unwrap().to_string();
    assert_eq!(book["title"], "Dune");
    assert_eq!(book["author"], "Frank Herbert");

    // Get
    let response = app
        .clone()
        .oneshot(Request::builder().uri(format!("/books/{id}")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let fetched: Value = body_json(response).await;
    assert_eq!(fetched["title"], "Dune");

    // Update
    let update = json_request(
        http::Method::PUT,
        &format!("/books/{id}"),
        json!({"year": 1966}),
    );
    let response = app.clone().oneshot(update).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let updated: Value = body_json(response).await;
    assert_eq!(updated["year"], 1966);
    assert_eq!(updated["title"], "Dune");

    // List
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let list: Value = body_json(response).await;
    assert_eq!(list.as_array().unwrap().len(), 1);

    // Delete
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(http::Method::DELETE)
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NO_CONTENT);

    // Get after delete
    let response = app
        .oneshot(Request::builder().uri(format!("/books/{id}")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn filter_books_by_author() {
    let app = create_app(":memory:").unwrap();

    for (title, author) in [("Book A", "Alice"), ("Book B", "Bob"), ("Book C", "Alice")] {
        let req = json_request(
            http::Method::POST,
            "/books",
            json!({"title": title, "author": author}),
        );
        let response = app.clone().oneshot(req).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);
    }

    let response = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let list: Value = body_json(response).await;
    assert_eq!(list.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn create_book_rejects_missing_fields() {
    let app = create_app(":memory:").unwrap();

    let missing_title = json_request(
        http::Method::POST,
        "/books",
        json!({"author": "Author"}),
    );
    let response = app.clone().oneshot(missing_title).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    let missing_author = json_request(
        http::Method::POST,
        "/books",
        json!({"title": "Title"}),
    );
    let response = app.clone().oneshot(missing_author).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    let empty_title = json_request(
        http::Method::POST,
        "/books",
        json!({"title": "   ", "author": "Author"}),
    );
    let response = app.oneshot(empty_title).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn update_missing_book_returns_404() {
    let app = create_app(":memory:").unwrap();

    let update = json_request(
        http::Method::PUT,
        "/books/nonexistent",
        json!({"title": "New Title"}),
    );
    let response = app.oneshot(update).await.unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
