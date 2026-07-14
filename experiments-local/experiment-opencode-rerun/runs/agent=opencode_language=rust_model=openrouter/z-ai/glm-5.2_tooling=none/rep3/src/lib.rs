pub mod db;
pub mod error;
pub mod handlers;
pub mod models;
pub mod state;

use std::sync::Arc;

use axum::{routing::get, Router};
use rusqlite::Connection;
use std::sync::Mutex;

use crate::state::AppState;

pub fn build_router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", get(handlers::list_books).post(handlers::create_book))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}

pub fn init_state(path: &str) -> anyhow::Result<Arc<AppState>> {
    let conn = if path == ":memory:" {
        Connection::open_in_memory()?
    } else {
        Connection::open(path)?
    };
    db::init(&conn)?;
    Ok(Arc::new(AppState {
        conn: Mutex::new(conn),
    }))
}
