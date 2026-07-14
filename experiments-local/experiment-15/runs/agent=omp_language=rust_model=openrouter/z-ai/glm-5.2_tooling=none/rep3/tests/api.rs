use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use book_collection::{build_router, AppState};

async fn body_json(body: Body) -> Value {
    let bytes = body.collect().await.expect("collect body").to_bytes();
    serde_json::from_slice(&bytes).expect("json body")
}

fn app() -> axum::Router {
    let state = AppState::in_memory().expect("in-memory db");
    build_router(state)
}

#[tokio::test]
async fn create_and_get_book_flow() {
    let app = app();

    // Create
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "The Pragmatic Programmer",
                        "author": "Andrew Hunt",
                        "year": 1999,
                        "isbn": "978-0201616224"
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let created = body_json(resp.into_body()).await;
    let id = created["id"].as_i64().expect("id present");
    assert_eq!(created["title"], "The Pragmatic Programmer");
    assert_eq!(created["author"], "Andrew Hunt");
    assert_eq!(created["year"], 1999);

    // GET /books/{id}
    let resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let fetched = body_json(resp.into_body()).await;
    assert_eq!(fetched["id"], id);
    assert_eq!(fetched["isbn"], "978-0201616224");
}

#[tokio::test]
async fn create_rejects_missing_title_and_author() {
    let app = app();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "",
                        "author": ""
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let body = body_json(resp.into_body()).await;
    assert!(body["error"].as_str().unwrap().contains("title"));

    // Missing author only
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "T",
                        "author": "  "
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let body = body_json(resp.into_body()).await;
    assert!(body["error"].as_str().unwrap().contains("author"));
}

#[tokio::test]
async fn list_supports_author_filter() {
    let app = app();

    async fn create(app: axum::Router, title: String, author: String) {
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&json!({ "title": title, "author": author })).unwrap(),
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }
    create(app.clone(), "Book A".to_string(), "Alice".to_string()).await;
    create(app.clone(), "Book B".to_string(), "Bob".to_string()).await;
    create(app.clone(), "Book C".to_string(), "Alice".to_string()).await;

    // No filter -> 3
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/books")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let body = body_json(resp.into_body()).await;
    assert_eq!(body["books"].as_array().unwrap().len(), 3);

    // Filter author=Alice -> 2
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let body = body_json(resp.into_body()).await;
    let books = body["books"].as_array().unwrap();
    assert_eq!(books.len(), 2);
    assert!(books
        .iter()
        .all(|b| b["author"].as_str().unwrap() == "Alice"));
}

#[tokio::test]
async fn update_and_delete_book() {
    let app = app();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "Old",
                        "author": "Old Author",
                        "year": 2000
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    let created = body_json(resp.into_body()).await;
    let id = created["id"].as_i64().unwrap();

    // Update
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "New Title",
                        "author": "New Author",
                        "year": 2020
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let updated = body_json(resp.into_body()).await;
    assert_eq!(updated["title"], "New Title");
    assert_eq!(updated["author"], "New Author");
    assert_eq!(updated["year"], 2020);

    // Delete
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    // Get -> 404
    let resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_check() {
    let app = app();
    let resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_json(resp.into_body()).await;
    assert_eq!(body["status"], "ok");
}
