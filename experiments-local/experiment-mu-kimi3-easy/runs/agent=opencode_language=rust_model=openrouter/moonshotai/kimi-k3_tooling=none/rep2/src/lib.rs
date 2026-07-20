//! A small REST API for managing a book collection, backed by SQLite.

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex};

use axum::{
    routing::{get, post},
    Router,
};

/// Shared application state: a single SQLite connection guarded by a mutex.
pub struct AppState {
    pub db: Mutex<rusqlite::Connection>,
}

impl AppState {
    pub fn new(conn: rusqlite::Connection) -> Self {
        Self {
            db: Mutex::new(conn),
        }
    }
}

/// Open (or create) the SQLite database at `path` and run migrations.
///
/// Pass `":memory:"` for an ephemeral in-memory database (used by tests).
pub fn init_db(path: &str) -> rusqlite::Result<rusqlite::Connection> {
    let conn = match path {
        ":memory:" => rusqlite::Connection::open_in_memory()?,
        _ => rusqlite::Connection::open(path)?,
    };
    db::init(&conn)?;
    Ok(conn)
}

/// Build the HTTP router with all endpoints wired to `state`.
pub fn build_router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            post(handlers::create_book).get(handlers::list_books),
        )
        .route(
            "/books/{id}",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
