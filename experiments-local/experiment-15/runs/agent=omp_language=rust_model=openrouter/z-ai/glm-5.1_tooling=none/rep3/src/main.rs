mod db;
mod errors;
mod handlers;
mod models;

use axum::routing::{delete, get, post, put};
use axum::Router;
use sqlx::SqlitePool;

fn app(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(pool)
}

#[tokio::main]
async fn main() {
    let pool = db::init_pool()
        .await
        .expect("failed to initialize database");
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind port 3000");
    println!("Listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app(pool))
        .await
        .expect("server error");
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use serde_json::json;
    use tower::ServiceExt;

    async fn test_pool() -> SqlitePool {
        let pool = SqlitePool::connect(":memory:").await.unwrap();
        sqlx::query(
            r#"
            CREATE TABLE books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            "#,
        )
        .execute(&pool)
        .await
        .unwrap();
        pool
    }

    fn make_app(pool: SqlitePool) -> Router {
        app(pool)
    }

    #[tokio::test]
    async fn health_check() {
        let pool = test_pool().await;
        let app = make_app(pool);
        let req = Request::builder()
            .uri("/health")
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = resp.into_body().collect().await.unwrap().to_bytes();
        assert_eq!(&body[..], b"ok");
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let pool = test_pool().await;
        let app = make_app(pool);
        let req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                json!({"title": "The Rust Book", "author": "Steve", "year": 2024}).to_string(),
            ))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
        let body: serde_json::Value =
            serde_json::from_slice(&resp.into_body().collect().await.unwrap().to_bytes()).unwrap();
        let id = body["id"].as_str().unwrap();

        // Fetch it back
        let pool = test_pool().await;
        let app = make_app(pool.clone());
        // Insert directly for the GET test
        sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
            .bind(id)
            .bind("The Rust Book")
            .bind("Steve")
            .bind(2024)
            .bind(Option::<String>::None)
            .execute(&pool)
            .await
            .unwrap();

        let req = Request::builder()
            .uri(&format!("/books/{}", id))
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body: serde_json::Value =
            serde_json::from_slice(&resp.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(body["title"], "The Rust Book");
    }

    #[tokio::test]
    async fn create_book_validation() {
        let pool = test_pool().await;
        let app = make_app(pool);
        let req = Request::builder()
            .method("POST")
            .uri("/books")
            .header("content-type", "application/json")
            .body(Body::from(
                json!({"title": "", "author": "Someone"}).to_string(),
            ))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn list_books_with_author_filter() {
        let pool = test_pool().await;
        sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
            .bind("1")
            .bind("Book A")
            .bind("Alice")
            .bind(2020)
            .bind(Option::<String>::None)
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
            .bind("2")
            .bind("Book B")
            .bind("Bob")
            .bind(2021)
            .bind(Option::<String>::None)
            .execute(&pool)
            .await
            .unwrap();

        let app = make_app(pool);
        let req = Request::builder()
            .uri("/books?author=Alice")
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body: serde_json::Value =
            serde_json::from_slice(&resp.into_body().collect().await.unwrap().to_bytes()).unwrap();
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["author"], "Alice");
    }

    #[tokio::test]
    async fn get_nonexistent_book() {
        let pool = test_pool().await;
        let app = make_app(pool);
        let req = Request::builder()
            .uri("/books/nope")
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn delete_book() {
        let pool = test_pool().await;
        sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
            .bind("del1")
            .bind("ToDelete")
            .bind("Author")
            .bind(2023)
            .bind(Option::<String>::None)
            .execute(&pool)
            .await
            .unwrap();

        let app = make_app(pool);
        let req = Request::builder()
            .method("DELETE")
            .uri("/books/del1")
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::NO_CONTENT);
    }

    #[tokio::test]
    async fn update_book() {
        let pool = test_pool().await;
        sqlx::query("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)")
            .bind("upd1")
            .bind("Old Title")
            .bind("Author")
            .bind(2020)
            .bind(Option::<String>::None)
            .execute(&pool)
            .await
            .unwrap();

        let app = make_app(pool);
        let req = Request::builder()
            .method("PUT")
            .uri("/books/upd1")
            .header("content-type", "application/json")
            .body(Body::from(
                json!({"title": "New Title"}).to_string(),
            ))
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body: serde_json::Value =
            serde_json::from_slice(&resp.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(body["title"], "New Title");
        assert_eq!(body["author"], "Author");
    }
}
