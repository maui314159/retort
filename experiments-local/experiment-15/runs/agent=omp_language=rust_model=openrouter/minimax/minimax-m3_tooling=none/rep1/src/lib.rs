//! Library entry point exposing the router, state, and modules so that
//! integration tests can drive the application through `tower::ServiceExt`.

pub mod db;
pub mod error;
pub mod handlers;
pub mod models;
pub mod state;

use axum::{
    routing::{delete, get, post, put},
    Router,
};

pub use state::AppState;

/// Build the application router with all routes wired up.
pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route(
            "/books",
            post(handlers::create_book).get(handlers::list_books),
        )
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .with_state(state)
}
