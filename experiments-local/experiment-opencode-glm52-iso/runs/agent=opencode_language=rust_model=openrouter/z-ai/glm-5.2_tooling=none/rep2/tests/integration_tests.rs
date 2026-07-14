use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use axum::response::Response;
use books_api::app;
use tower::ServiceExt;

async fn setup_app() -> axum::Router {
    let db = books_api::db::init_db().unwrap();
    app(db)
}

async fn send(app: axum::Router, method: Method, uri: &str, body: Option<String>) -> Response {
    let request = match body {
        Some(b) => Request::builder()
            .method(method.clone())
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(b))
            .unwrap(),
        None => Request::builder()
            .method(method)
            .uri(uri)
            .body(Body::empty())
            .unwrap(),
    };
    app.oneshot(request).await.unwrap()
}

async fn body_text(resp: Response) -> String {
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    String::from_utf8(bytes.to_vec()).unwrap()
}

#[tokio::test]
async fn create_get_and_delete_book() {
    let app = setup_app().await;
    let payload = r#"{"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"123"}"#;
    let resp = send(app.clone(), Method::POST, "/books", Some(payload.to_string())).await;
    assert_eq!(resp.status(), StatusCode::CREATED);
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    let id = v["id"].as_i64().unwrap();

    let resp = send(app.clone(), Method::GET, &format!("/books/{}", id), None).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    assert_eq!(v["title"], "The Hobbit");

    let resp = send(app.clone(), Method::DELETE, &format!("/books/{}", id), None).await;
    assert_eq!(resp.status(), StatusCode::NO_CONTENT);

    let resp = send(app.clone(), Method::GET, &format!("/books/{}", id), None).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn validation_rejects_empty_title() {
    let app = setup_app().await;
    let payload = r#"{"title":"","author":"someone"}"#;
    let resp = send(app, Method::POST, "/books", Some(payload.to_string())).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    assert!(v["error"].as_str().unwrap().contains("title"));
}

#[tokio::test]
async fn list_books_with_author_filter() {
    let app = setup_app().await;
    let p1 = r#"{"title":"A","author":"Asimov","year":1950}"#;
    let p2 = r#"{"title":"B","author":"Tolkien","year":1937}"#;
    let _ = send(app.clone(), Method::POST, "/books", Some(p1.to_string())).await;
    let _ = send(app.clone(), Method::POST, "/books", Some(p2.to_string())).await;

    let resp = send(app.clone(), Method::GET, "/books?author=Asimov", None).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    let arr = v.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert_eq!(arr[0]["author"], "Asimov");

    let resp = send(app, Method::GET, "/books", None).await;
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    assert_eq!(v.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn update_book_fields() {
    let app = setup_app().await;
    let payload = r#"{"title":"Old","author":"A","year":2000}"#;
    let resp = send(app.clone(), Method::POST, "/books", Some(payload.to_string())).await;
    let v: serde_json::Value = serde_json::from_str(&body_text(resp).await).unwrap();
    let id = v["id"].as_i64().unwrap();

    let upd = r#"{"title":"New"}"#;
    let resp = send(app.clone(), Method::PUT, &format!("/books/{}", id), Some(upd.to_string())).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let v: serde_json::Value = serde_json::from_str(&body_text(resp).await).unwrap();
    assert_eq!(v["title"], "New");
    assert_eq!(v["author"], "A");
    assert_eq!(v["year"], 2000);
}

#[tokio::test]
async fn health_check_ok() {
    let app = setup_app().await;
    let resp = send(app, Method::GET, "/health", None).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let txt = body_text(resp).await;
    let v: serde_json::Value = serde_json::from_str(&txt).unwrap();
    assert_eq!(v["status"], "ok");
}
