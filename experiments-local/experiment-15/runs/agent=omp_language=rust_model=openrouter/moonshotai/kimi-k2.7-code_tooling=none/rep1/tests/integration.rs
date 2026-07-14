use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
    response::Response,
};
use book_api::app;
use serde_json::{json, Value};
use tower::ServiceExt;

async fn response_body(resp: Response) -> Value {
    let bytes = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap_or(Value::Null)
}

fn json_request(method: &str, uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("Content-Type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

#[tokio::test]
async fn health_check_returns_ok() {
    let resp = app().oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap()).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = response_body(resp).await;
    assert_eq!(body, json!({"status": "ok"}));
}

#[tokio::test]
async fn create_and_get_book() {
    let app = app();

    let create_resp = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({
                "title": "The Rust Programming Language",
                "author": "Steve Klabnik",
                "year": 2019,
                "isbn": "978-1593278281"
            }),
        ))
        .await
        .unwrap();
    assert_eq!(create_resp.status(), StatusCode::CREATED);
    let created: Value = response_body(create_resp).await;
    let id = created["id"].as_u64().unwrap() as u32;

    let get_resp = app
        .oneshot(Request::builder().uri(format!("/books/{id}")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(get_resp.status(), StatusCode::OK);
    let fetched: Value = response_body(get_resp).await;
    assert_eq!(fetched["title"], "The Rust Programming Language");
    assert_eq!(fetched["author"], "Steve Klabnik");
    assert_eq!(fetched["year"], 2019);
    assert_eq!(fetched["isbn"], "978-1593278281");
}

#[tokio::test]
async fn list_books_filtered_by_author() {
    let app = app();

    app.clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({"title": "Book A", "author": "Author X", "year": 2020}),
        ))
        .await
        .unwrap();
    app.clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({"title": "Book B", "author": "Author Y", "year": 2021}),
        ))
        .await
        .unwrap();

    let resp = app
        .oneshot(Request::builder().uri("/books?author=Author%20X").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = response_body(resp).await;
    let books = body.as_array().unwrap();
    assert_eq!(books.len(), 1);
    assert_eq!(books[0]["title"], "Book A");
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = app();

    let create_resp = app
        .clone()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({"title": "Old Title", "author": "Old Author"}),
        ))
        .await
        .unwrap();
    let created: Value = response_body(create_resp).await;
    let id = created["id"].as_u64().unwrap() as u32;

    let update_resp = app
        .clone()
        .oneshot(json_request(
            "PUT",
            &format!("/books/{id}"),
            json!({"title": "New Title", "author": "New Author", "year": 2023}),
        ))
        .await
        .unwrap();
    assert_eq!(update_resp.status(), StatusCode::OK);
    let updated: Value = response_body(update_resp).await;
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["year"], 2023);

    let delete_resp = app
        .clone()
        .oneshot(Request::builder().method("DELETE").uri(format!("/books/{id}")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(delete_resp.status(), StatusCode::NO_CONTENT);

    let get_resp = app
        .oneshot(Request::builder().uri(format!("/books/{id}")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(get_resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn create_book_rejects_missing_title() {
    let resp = app()
        .oneshot(json_request(
            "POST",
            "/books",
            json!({"author": "Some Author"}),
        ))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let body = response_body(resp).await;
    assert!(body["error"].as_str().unwrap().contains("title"));
}
