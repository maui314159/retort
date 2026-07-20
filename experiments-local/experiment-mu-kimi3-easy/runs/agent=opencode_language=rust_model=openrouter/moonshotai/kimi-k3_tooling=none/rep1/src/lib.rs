//! Book collection REST API — library crate.
//!
//! Exposes [`build_router`] so both the binary and the integration tests can
//! construct the same axum application over any `rusqlite` connection
//! (file-backed in production, in-memory in tests).

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex, MutexGuard};

use axum::{routing::get, Router};
use rusqlite::Connection;

/// Shared application state: a single SQLite connection behind a mutex.
///
/// `rusqlite::Connection` is `Send` but not `Sync`, so a `Mutex` is required
/// to share it across axum's worker tasks. Contention is not a concern at
/// this scale and SQLite serializes writers anyway.
#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

impl AppState {
    pub fn new(conn: Connection) -> Self {
        Self {
            db: Arc::new(Mutex::new(conn)),
        }
    }

    /// Lock the shared connection. A poisoned mutex means a previous request
    /// panicked while holding it; there is no meaningful recovery, so we
    /// propagate the panic.
    pub fn conn(&self) -> MutexGuard<'_, Connection> {
        self.db.lock().expect("database mutex poisoned")
    }
}

/// Build the HTTP router with all API routes mounted.
pub fn build_router(state: AppState) -> Router {
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
