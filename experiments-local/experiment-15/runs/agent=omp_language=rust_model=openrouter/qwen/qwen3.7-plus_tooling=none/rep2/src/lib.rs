pub mod db;
pub mod handlers;
pub mod models;

use axum::{routing::get, Router};
use sqlx::SqlitePool;

pub fn create_app(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(handlers::health_check))
        .route("/books", get(handlers::list_books).post(handlers::create_book))
        .route("/books/:id", get(handlers::get_book).put(handlers::update_book).delete(handlers::delete_book))
        .with_state(pool)
}
