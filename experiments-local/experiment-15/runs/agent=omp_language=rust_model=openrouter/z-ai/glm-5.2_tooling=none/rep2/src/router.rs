use axum::routing::{get, post};
use axum::Router;

use crate::handlers::{create_book, delete_book, get_book, health, list_books, update_book, AppState};

/// Build the application router with the given shared state.
pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}
