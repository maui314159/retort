//! Integration tests that exercise the full HTTP router against an isolated
//! SQLite database.

use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::handlers::app_routes;
use http_body_util::BodyExt;
use sqlx::sqlite::SqlitePoolOptions;
use sqlx::SqlitePool;
use tower::ServiceExt;

async fn setup() -> SqlitePool {
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect("sqlite::memory:")
        .await
        .expect("connect memory db");
    book_api::db::init_db(&pool).await.expect("init db");
    pool
}

async fn body_string(body: Body) -> String {
    let bytes = body.into_data_stream().collect().await.unwrap();
    String::from_utf8(bytes.to_bytes().to_vec()).unwrap()
}

#[tokio::test]
async fn create_get_and_list_book() {
    let pool = setup().await;
    let app = app_routes(pool.clone());

    let payload = r#"{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780261103283"}"#;
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let body = body_string(resp.into_body()).await;
    assert!(body.contains("The Hobbit"));
    assert!(body.contains("\"id\":"));

    // GET /books
    let resp = app
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_string(resp.into_body()).await;
    assert!(body.contains("The Hobbit"));

    // GET /books/1
    let resp = app
        .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_string(resp.into_body()).await;
    assert!(body.contains("\"id\":1"));
    assert!(body.contains("J.R.R. Tolkien"));
}

#[tokio::test]
async fn validation_rejects_empty_title_and_author() {
    let pool = setup().await;
    let app = app_routes(pool.clone());

    // Empty title -> 400
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"title":"   ","author":"X"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    // Missing author field -> 422 (axum Json rejection; field required)
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"title":"Only Title"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn update_then_delete_book() {
    let pool = setup().await;
    let app = app_routes(pool.clone());

    // Seed a book.
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"title":"Dune","author":"Frank Herbert","year":1965}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    // PUT /books/1 — update year and title.
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/books/1")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"title":"Dune (Revised)","author":"Frank Herbert","year":1966}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_string(resp.into_body()).await;
    assert!(body.contains("Dune (Revised)"));

    // DELETE /books/1 -> 204
    let resp = app
        .clone()
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

    // GET /books/1 -> 404
    let resp = app
        .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn author_filter_works() {
    let pool = setup().await;
    let app = app_routes(pool.clone());

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
                    .body(Body::from(format!(
                        r#"{{"title":"{title}","author":"{author}"}}"#
                    )))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
    }

    let resp = app
        .oneshot(
            Request::builder()
                .uri("/books?author=Alice")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_string(resp.into_body()).await;
    assert!(body.contains("Alice"));
    assert!(!body.contains("Bob"));
}

#[tokio::test]
async fn health_check_ok() {
    let pool = setup().await;
    let app = app_routes(pool.clone());
    let resp = app
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}
