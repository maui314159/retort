use books_api::db;
use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use std::sync::atomic::{AtomicU64, Ordering};
use tower::ServiceExt;

static COUNTER: AtomicU64 = AtomicU64::new(0);

async fn setup() -> sqlx::SqlitePool {
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let pid = std::process::id();
    let path = std::env::temp_dir().join(format!("books_api_test_{pid}_{n}.db"));
    // ensure fresh file
    let _ = std::fs::remove_file(&path);
    let url = format!("sqlite:{}", path.display());
    db::init_pool(&url).await.expect("init pool")
}

async fn body_to_json(body: Body) -> Value {
    let bytes = body.collect().await.unwrap().to_bytes();
    if bytes.is_empty() {
        return Value::Null;
    }
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_returns_ok() {
    let pool = setup().await;
    let app = books_api::app(pool);

    let res = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(res.status(), StatusCode::OK);
    let json = body_to_json(res.into_body()).await;
    assert_eq!(json["status"], "ok");
}

#[tokio::test]
async fn create_list_get_update_delete_book() {
    let pool = setup().await;
    let app = books_api::app(pool);

    // Create
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({
                        "title": "The Pragmatic Programmer",
                        "author": "Hunt",
                        "year": 1999,
                        "isbn": "9780201616224"
                    }))
                    .unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CREATED);
    let created = body_to_json(res.into_body()).await;
    let id = created["id"].as_i64().unwrap();

    // List
    let res = app
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let list = body_to_json(res.into_body()).await;
    assert_eq!(list.as_array().unwrap().len(), 1);

    // List with author filter
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Hunt")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let list = body_to_json(res.into_body()).await;
    assert_eq!(list.as_array().unwrap().len(), 1);

    // Filter with no match
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/books?author=Unknown")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let list = body_to_json(res.into_body()).await;
    assert_eq!(list.as_array().unwrap().len(), 0);

    // Get
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let fetched = body_to_json(res.into_body()).await;
    assert_eq!(fetched["title"], "The Pragmatic Programmer");

    // Update
    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{id}"))
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({ "year": 2000 })).unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::OK);
    let updated = body_to_json(res.into_body()).await;
    assert_eq!(updated["year"], 2000);
    assert_eq!(updated["title"], "The Pragmatic Programmer");

    // Delete
    let res = app
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
    assert_eq!(res.status(), StatusCode::NO_CONTENT);

    // Get after delete -> 404
    let res = app
        .oneshot(
            Request::builder()
                .uri(format!("/books/{id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_rejects_missing_fields() {
    let pool = setup().await;
    let app = books_api::app(pool);

    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({ "title": "", "author": "" })).unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);

    // missing required field entirely (serde error path -> axum default 400)
    let res = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&json!({ "year": 2020 })).unwrap(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn isbn_is_unique() {
    let pool = setup().await;
    let app = books_api::app(pool);

    let create = |isbn: &'static str| {
        json!({
            "title": "A",
            "author": "B",
            "isbn": isbn
        })
    };

    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_vec(&create("111")).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CREATED);

    let res = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(serde_json::to_vec(&create("111")).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(res.status(), StatusCode::CONFLICT);
}
