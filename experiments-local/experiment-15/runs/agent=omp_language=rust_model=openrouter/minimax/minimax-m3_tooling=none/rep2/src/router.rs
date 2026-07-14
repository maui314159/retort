//! Router construction.
//!
//! `build_router` is the single entry point used by both the binary
//! (`main.rs`) and the integration tests. It is pure with respect to its
//! arguments: it does not open sockets or touch a database.

use axum::routing::get;
use axum::Router;
use sqlx::Pool;
use sqlx::Sqlite;
use tower_http::trace::TraceLayer;

use crate::handlers::{
    create_book, delete_book, get_book, health, list_books, update_book, AppState,
};

/// Build the application's [`Router`] for a SQLite connection pool.
pub fn build_router(pool: Pool<Sqlite>) -> Router {
    let state = AppState { pool };
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
