mod db;
mod error;
mod handlers;
mod models;

use axum::routing::{get, post};
use axum::Router;
use db::Db;
use std::env;
use std::net::SocketAddr;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("book_api=info".parse()?))
        .init();

    let db_path =
        env::var("BOOK_DB").unwrap_or_else(|_| "books.db".to_string());
    let db = Db::open(&db_path)?;

    let app = build_router(db);

    let addr: SocketAddr =
        env::var("BOOK_ADDR").unwrap_or_else(|_| "127.0.0.1:8080".to_string()).parse()?;
    tracing::info!("listening on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

pub fn build_router(db: Db) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(db)
}

#[cfg(test)]
mod router_tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    fn fresh_db() -> Db {
        Db::in_memory().expect("in-memory db")
    }

    async fn body_text(resp: axum::response::Response) -> String {
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        String::from_utf8(bytes.to_vec()).unwrap()
    }

    #[tokio::test]
    async fn health_returns_ok() {
        let app = build_router(fresh_db());
        let resp = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(body_text(resp).await, "ok");
    }

    #[tokio::test]
    async fn validation_rejects_missing_title() {
        let app = build_router(fresh_db());
        let body = Body::from(r#"{"author":"A"}"#);
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(body)
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn full_crud_lifecycle() {
        let app = build_router(fresh_db());

        let create_body = Body::from(
            r#"{"title":"Rust in Action","author":"Tim McNamara","year":2017,"isbn":"9781617294537"}"#,
        );
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(create_body)
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
        let text = body_text(resp).await;
        let book: models::Book = serde_json::from_str(&text).unwrap();
        assert_eq!(book.id, 1);
        assert_eq!(book.title, "Rust in Action");

        let resp = app
            .clone()
            .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);

        let upd_body = Body::from(r#"{"year":2018}"#);
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("PUT")
                    .uri("/books/1")
                    .header("content-type", "application/json")
                    .body(upd_body)
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let text = body_text(resp).await;
        let b: models::Book = serde_json::from_str(&text).unwrap();
        assert_eq!(b.year, Some(2018));

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

        let resp = app
            .oneshot(Request::builder().uri("/books/1").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn author_filter_works() {
        let app = build_router(fresh_db());
        for body in [
                r#"{"title":"A","author":"Alice","year":2001}"#,
                r#"{"title":"B","author":"Bob","year":2002}"#,
                r#"{"title":"C","author":"Alice","year":2003}"#,
        ] {
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
            .oneshot(
                Request::builder()
                    .uri("/books?author=Alice")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let text = body_text(resp).await;
        let books: Vec<models::Book> = serde_json::from_str(&text).unwrap();
        assert_eq!(books.len(), 2);
        assert!(books.iter().all(|b| b.author == "Alice"));
    }

    #[tokio::test]
    async fn isbn_conflict_returns_409() {
        let app = build_router(fresh_db());
        let b1 = Body::from(r#"{"title":"X","author":"A","isbn":"111"}"#);
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(b1)
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);

        let b2 = Body::from(r#"{"title":"Y","author":"B","isbn":"111"}"#);
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(b2)
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CONFLICT);
    }
}
