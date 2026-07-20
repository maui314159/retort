//! Library root for the book collection REST API.

pub mod db;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex};

use axum::{routing::get, Router};
use rusqlite::Connection;

use crate::handlers::AppState;

/// Build the application router backed by the given SQLite connection.
///
/// The schema is created if it does not exist yet. The connection is shared
/// between handlers behind a mutex; rusqlite is synchronous, which is fine
/// for an embedded database at this scale.
pub fn build_app(conn: Connection) -> Router {
    db::init_schema(&conn).expect("failed to initialize database schema");
    let state = Arc::new(AppState {
        conn: Mutex::new(conn),
    });

    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            get(handlers::list_books).post(handlers::create_book),
        )
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
