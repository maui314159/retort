use axum::body::Body;
use axum::http::{Request, StatusCode};
use book_api::{build_app, init_db, make_pool, AppState};
use http_body_util::BodyExt;
use tower::ServiceExt;

async fn body_to_string(body: Body) -> String {
    let bytes = body.into_data_stream().collect().await.unwrap().to_bytes();
    String::from_utf8(bytes.to_vec()).unwrap()
}

fn temp_pool() -> AppState {
    let dir = tempfile_dir();
    std::fs::create_dir_all(&dir).ok();
    let path = format!("{}/test.db", dir);
    std::fs::remove_file(&path).ok();
    let pool = make_pool(&path);
    init_db(&pool).unwrap();
    AppState { pool }
}

fn tempfile_dir() -> String {
    format!("/tmp/book-api-tests-{}", std::process::id())
}

async fn create_book(app: &axum::Router, body: &str) -> (StatusCode, String) {
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
    let status = resp.status();
    (status, body_to_string(resp.into_body()).await)
}

#[tokio::test]
async fn create_and_get_book() {
    let state = temp_pool();
    let app = build_app(state);

    let (status, body) = create_book(
        &app,
        r#"{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"123"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let v: serde_json::Value = serde_json::from_str(&body).unwrap();
    let id = v["id"].as_i64().unwrap();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_to_string(resp.into_body()).await;
    let v: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert_eq!(v["title"], "The Hobbit");
    assert_eq!(v["author"], "Tolkien");
    assert_eq!(v["year"], 1937);
}

#[tokio::test]
async fn validation_rejects_empty_title() {
    let state = temp_pool();
    let app = build_app(state);
    let (status, _body) = create_book(&app, r#"{"title":"","author":"Tolkien"}"#).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, _body) = create_book(&app, r#"{"title":"X","author":""}"#).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn list_with_author_filter() {
    let state = temp_pool();
    let app = build_app(state);
    create_book(&app, r#"{"title":"A","author":"Asimov"}"#).await;
    create_book(&app, r#"{"title":"B","author":"Clarke"}"#).await;
    create_book(&app, r#"{"title":"C","author":"Asimov"}"#).await;

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/books?author=Asimov")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_to_string(resp.into_body()).await;
    let v: serde_json::Value = serde_json::from_str(&body).unwrap();
    let arr = v.as_array().unwrap();
    assert_eq!(arr.len(), 2);
    for b in arr {
        assert_eq!(b["author"], "Asimov");
    }
}

#[tokio::test]
async fn update_and_delete_book() {
    let state = temp_pool();
    let app = build_app(state);
    let (status, body) = create_book(&app, r#"{"title":"Old","author":"A"}"#).await;
    assert_eq!(status, StatusCode::CREATED);
    let id: i64 = serde_json::from_str::<serde_json::Value>(&body).unwrap()["id"]
        .as_i64()
        .unwrap();

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(format!("/books/{}", id))
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"title":"New","author":"B","year":2000}"#.to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_to_string(resp.into_body()).await;
    let v: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert_eq!(v["title"], "New");
    assert_eq!(v["author"], "B");

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/books/{}", id))
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
                .uri(format!("/books/{}", id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_ok() {
    let state = temp_pool();
    let app = build_app(state);
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
}
