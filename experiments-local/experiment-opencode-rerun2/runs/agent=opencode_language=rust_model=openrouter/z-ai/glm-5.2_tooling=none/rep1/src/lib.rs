mod db;
mod handlers;
mod models;

use axum::routing::{get, post};
use axum::Router;
use sqlx::SqlitePool;

pub fn app(pool: SqlitePool) -> Router {
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

pub async fn run() {
    use std::env;
    let db_url =
        env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db?mode=rwc".to_string());
    let pool = db::init_pool(&db_url).await;
    let addr = env::var("LISTEN_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind");
    println!("listening on {addr}");
    axum::serve(listener, app(pool)).await.expect("server failed");
}
