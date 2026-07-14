pub mod db;
pub mod error;
pub mod handlers;
pub mod models;

use axum::routing::{get, post};
use axum::Router;
use db::Db;
use tower::ServiceBuilder;

pub fn app(database: Db) -> Router {
    Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book).get(handlers::list_books))
        .route(
            "/books/:id",
            get(handlers::get_book)
                .put(handlers::update_book)
                .delete(handlers::delete_book),
        )
        .layer(ServiceBuilder::new())
        .with_state(database)
}
