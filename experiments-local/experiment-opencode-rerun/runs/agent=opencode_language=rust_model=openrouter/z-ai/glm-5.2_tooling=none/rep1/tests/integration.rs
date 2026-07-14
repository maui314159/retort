use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::app_router;
use book_api::db::Db;
use serde_json::json;
use tower::ServiceExt;

fn test_app() -> axum::Router {
    let db = Db::open_in_memory().expect("open in-memory db");
    app_router(db)
}

async fn create_book(app: &axum::Router, body: serde_json::Value) -> serde_json::Value {
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn create_list_get_update_delete_flow() {
    let app = test_app();

    let created = create_book(
        &app,
        json!({
            "title": "The Rust Book",
            "author": "Jane Doe",
            "year": 2021,
            "isbn": "978-3-16-148410-0"
        }),
    )
    .await;
    assert_eq!(created["title"], "The Rust Book");
    let id = created["id"].as_i64().unwrap();

    // list
    let resp = app
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let list: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(list.as_array().unwrap().len(), 1);

    // get by id
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let got: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(got["author"], "Jane Doe");

    // update
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({ "title": "The Rust Book, 2nd Ed." }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let updated: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(updated["title"], "The Rust Book, 2nd Ed.");
    assert_eq!(updated["author"], "Jane Doe");

    // delete
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

    // get after delete -> 404
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_requires_title_and_author() {
    let app = test_app();

    // empty title
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(json!({ "title": "", "author": "A" }).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // empty author
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(json!({ "title": "T", "author": "" }).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

    // missing fields entirely -> axum extractor rejects with 422
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(json!({ "author": "A" }).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn author_filter_works() {
    let app = test_app();
    create_book(&app, json!({ "title": "A", "author": "Alice" })).await;
    create_book(&app, json!({ "title": "B", "author": "Bob" })).await;
    create_book(&app, json!({ "title": "C", "author": "Alice" })).await;

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let list: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(list.as_array().unwrap().len(), 2);
    for b in list.as_array().unwrap() {
        assert_eq!(b["author"], "Alice");
    }
}

#[tokio::test]
async fn health_check_ok() {
    let app = test_app();
    let resp = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn get_missing_book_returns_404() {
    let app = test_app();
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books/999")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
