pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use std::sync::{Arc, Mutex};

use axum::{
    routing::{get, post},
    Router,
};
use rusqlite::Connection;

#[derive(Clone)]
pub struct AppState {
    pub conn: Arc<Mutex<Connection>>,
}

impl AppState {
    /// Open an in-memory SQLite database with an initialized schema. Useful for tests.
    pub fn in_memory() -> rusqlite::Result<Self> {
        let conn = Connection::open_in_memory()?;
        db::init(&conn)?;
        Ok(AppState {
            conn: Arc::new(Mutex::new(conn)),
        })
    }
}


pub fn build_router(state: AppState) -> Router {
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
