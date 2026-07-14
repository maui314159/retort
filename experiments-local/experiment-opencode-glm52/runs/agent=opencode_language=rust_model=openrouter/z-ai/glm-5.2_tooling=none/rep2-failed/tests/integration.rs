mod main;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use main::build_router;
use sqlx::{sqlite::SqlitePool, Sqlite};
use tower::ServiceExt;

async fn setup() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
    let _ = build_router(pool.clone()).await;
    pool
}

async fn body_to_text(body: Body) -> String {
    let bytes = body.into_body().collect().await.unwrap().to_bytes();
    String::from_utf8(bytes.to_vec()).unwrap()
}

#[tokio::test]
async fn create_get_and_delete_book() {
    let pool = setup().await;
    let app = build_router(pool.clone()).await;

    let create = r#"{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}"#;
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(create))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let body = body_to_text(resp.into_body()).await;
    assert!(body.contains("\"title\":\"Dune\""));
    assert!(body.contains("\"id\":1"));

    let app2 = build_router(pool.clone()).await;
    let resp = app2
        .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(body_to_text(resp.into_body()).await.contains("Dune"));

    let app3 = build_router(pool.clone()).await;
    let resp = app3
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri("/books/1")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let app4 = build_router(pool.clone()).await;
    let resp = app4
        .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_rejects_empty_fields() {
    let pool = setup().await;
    let app = build_router(pool.clone()).await;

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"title":"","author":"","year":2000}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter_and_health() {
    let pool = setup().await;
    let app = build_router(pool.clone()).await;

    for (title, author) in [
        ("Foundation", "Isaac Asimov"),
        ("I, Robot", "Isaac Asimov"),
        ("1984", "George Orwell"),
    ] {
        let body = format!("{{\"title\":\"{}\",\"author\":\"{}\"}}", title, author);
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(body))
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
                .uri("/books?author=Asimov")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let text = body_to_text(resp.into_body()).await;
    assert!(text.contains("Foundation"));
    assert!(text.contains("I, Robot"));
    assert!(!text.contains("1984"));

    let resp = app
        .clone()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(body_to_text(resp.into_body()).await.contains("ok"));
}

#[tokio::test]
async fn update_book() {
    let pool = setup().await;
    let app = build_router(pool.clone()).await;

    let create = r#"{"title":"Old","author":"A","year":2000}"#;
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(create))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    let update = r#"{"title":"New","year":2010}"#;
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/books/1")
                .header("content-type", "application/json")
                .body(Body::from(update))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let text = body_to_text(resp.into_body()).await;
    assert!(text.contains("\"title\":\"New\""));
    assert!(text.contains("\"year\":2010"));
    assert!(text.contains("\"author\":\"A\""));
}
