use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use book_collection::db;
use book_collection::handlers::AppState;
use book_collection::router;
use serde_json::{json, Value};
use tower::ServiceExt;

async fn setup() -> AppState {
    let pool = db::in_memory_pool().expect("in-memory pool");
    db::migrate(&pool).expect("migrate");
    AppState { pool }
}

async fn send(state: AppState, req: Request<Body>) -> (StatusCode, Value) {
    let response = router::app(state).oneshot(req).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let body: Value = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).unwrap_or(Value::Null)
    };
    (status, body)
}

fn json_request(method: &str, uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_vec(&body).unwrap()))
        .unwrap()
}

#[tokio::test]
async fn create_get_list_and_delete_book() {
    let state = setup().await;

    // Create
    let (status, body) = send(
        state.clone(),
        json_request("POST", "/books", json!({
            "title": "The Rust Book",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "9781718500443"
        })),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let id = body["id"].as_i64().expect("id present");
    assert_eq!(body["title"], "The Rust Book");
    assert_eq!(body["author"], "Steve Klabnik");
    assert_eq!(body["year"], 2019);

    // Get by id
    let (status, body) = send(
        state.clone(),
        Request::builder()
            .method("GET")
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["id"], id);

    // List
    let (status, body) = send(
        state.clone(),
        Request::builder()
            .method("GET")
            .uri("/books")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 1);

    // Delete
    let (status, _) = send(
        state.clone(),
        Request::builder()
            .method("DELETE")
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::NO_CONTENT);

    // Get again -> 404
    let (status, _) = send(
        state.clone(),
        Request::builder()
            .method("GET")
            .uri(format!("/books/{id}"))
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_rejects_missing_fields() {
    let state = setup().await;

    // Missing author
    let (status, body) = send(
        state.clone(),
        json_request("POST", "/books", json!({ "title": "No Author" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("author"));

    // Empty title
    let (status, body) = send(
        state.clone(),
        json_request("POST", "/books", json!({ "title": "  ", "author": "Someone" })),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].as_str().unwrap().contains("title"));

    // Malformed JSON — axum's Json extractor rejects with a 4xx status.
    let response = router::app(state)
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from("{not json"))
                .unwrap(),
        )
        .await
        .unwrap();
    assert!(
        response.status().is_client_error(),
        "malformed JSON should yield a 4xx, got {}",
        response.status()
    );
}

#[tokio::test]
async fn list_filters_by_author() {
    let state = setup().await;

    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Bob"),
        ("Book C", "Alice Munro"),
    ] {
        let (status, _) = send(
            state.clone(),
            json_request("POST", "/books", json!({ "title": title, "author": author })),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    // No filter -> 3
    let (status, body) = send(
        state.clone(),
        Request::builder().method("GET").uri("/books").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 3);

    // Filter author=Alice -> matches "Alice" and "Alice Munro"
    let (status, body) = send(
        state.clone(),
        Request::builder()
            .method("GET")
            .uri("/books?author=Alice")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn update_partial_fields() {
    let state = setup().await;
    let (_, body) = send(
        state.clone(),
        json_request("POST", "/books", json!({
            "title": "Original",
            "author": "Orig Author",
            "year": 2000
        })),
    )
    .await;
    let id = body["id"].as_i64().unwrap();

    // Update only the title
    let (status, body) = send(
        state.clone(),
        json_request("PUT", &format!("/books/{id}"), json!({ "title": "Updated" })),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["title"], "Updated");
    assert_eq!(body["author"], "Orig Author");
    assert_eq!(body["year"], 2000);

    // Empty update -> 400
    let (status, _) = send(
        state.clone(),
        json_request("PUT", &format!("/books/{id}"), json!({})),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    // Update non-existent -> 404
    let (status, _) = send(
        state.clone(),
        json_request("PUT", "/books/99999", json!({ "title": "X" })),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_ok() {
    let state = setup().await;
    let (status, body) = send(
        state.clone(),
        Request::builder().method("GET").uri("/health").body(Body::empty()).unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
}

#[tokio::test]
async fn model_validation_unit() {
    use book_collection::models::{CreateBook, UpdateBook};

    let bad = CreateBook { title: "".into(), author: "".into(), year: None, isbn: None };
    assert!(bad.validate().is_err());

    let good = CreateBook { title: "T".into(), author: "A".into(), year: Some(2020), isbn: None };
    assert!(good.validate().is_ok());

    let bad_year = CreateBook { title: "T".into(), author: "A".into(), year: Some(-1), isbn: None };
    assert!(bad_year.validate().is_err());

    let empty_update = UpdateBook::default();
    assert!(empty_update.validate().is_err());

    let partial = UpdateBook { title: Some("New".into()), ..Default::default() };
    assert!(partial.validate().is_ok());
}
