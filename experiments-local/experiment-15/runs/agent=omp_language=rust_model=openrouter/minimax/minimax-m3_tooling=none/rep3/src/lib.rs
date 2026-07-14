//! Library entry point for the books API.
//!
//! Exposes [`build_app`] (which constructs the axum router) and
//! [`AppState`] so tests and the binary can share the same wiring.

use axum::routing::{get, post};
use axum::Router;
use sqlx::SqlitePool;

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

pub use error::{AppError, AppResult};
pub use handlers::AppState;

/// Build the application's router. Pass the database pool as state.
pub fn build_app(pool: SqlitePool) -> Router {
    let state = AppState { pool };

    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
