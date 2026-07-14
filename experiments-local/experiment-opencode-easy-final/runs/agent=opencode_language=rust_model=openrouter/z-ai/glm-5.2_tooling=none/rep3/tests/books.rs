use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::{build_app, make_pool};
use http_body_util::BodyExt;
use std::sync::atomic::{AtomicU64, Ordering};
use tower::ServiceExt;

static COUNTER: AtomicU64 = AtomicU64::new(0);

async fn body_string(body: Body) -> String {
    let bytes = body.collect().await.unwrap().to_bytes();
    String::from_utf8(bytes.to_vec()).unwrap()
}

async fn setup_app() -> axum::Router {
    let id = COUNTER.fetch_add(1, Ordering::SeqCst);
    let path = format!("/tmp/book-api-test-{}-{}.db", std::process::id(), id);
    let _ = std::fs::remove_file(&path);
    let url = format!("sqlite:{}", path);
    let pool = make_pool(&url).await.unwrap();
    build_app(pool).await
}

#[tokio::test]
async fn create_and_get_book() {
    let app = setup_app().await;

    let create_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::json!({
                        "title": "The Hobbit",
                        "author": "J.R.R. Tolkien",
                        "year": 1937,
                        "isbn": "978-0261102217"
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(create_resp.status(), StatusCode::CREATED);
    let body = body_string(create_resp.into_body()).await;
    let created: serde_json::Value = serde_json::from_str(&body).unwrap();
    let id = created["id"].as_i64().unwrap();

    let get_resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(get_resp.status(), StatusCode::OK);
    let body = body_string(get_resp.into_body()).await;
    let fetched: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert_eq!(fetched["title"], "The Hobbit");
    assert_eq!(fetched["author"], "J.R.R. Tolkien");
}

#[tokio::test]
async fn validation_rejects_empty_title() {
    let app = setup_app().await;

    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::json!({ "title": "", "author": "Someone" }).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter_and_delete() {
    let app = setup_app().await;

    for (title, author) in [
        ("Book A", "Alice"),
        ("Book B", "Bob"),
        ("Book C", "Alice"),
    ] {
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::json!({ "title": title, "author": author }).to_string(),
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

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
    let body = body_string(resp.into_body()).await;
    let list: serde_json::Value = serde_json::from_str(&body).unwrap();
    let arr = list.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    for b in arr {
        assert_eq!(b["author"], "Alice");
    }

    let first_id = arr[0]["id"].as_i64().unwrap();
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", first_id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/books/{}", first_id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}
