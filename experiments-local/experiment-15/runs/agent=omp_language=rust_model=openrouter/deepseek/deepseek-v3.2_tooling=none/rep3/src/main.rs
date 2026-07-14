mod error;
mod handlers;
mod models;

use axum::{Router, routing::{get, post, put, delete}};
use sqlx::SqlitePool;
use std::net::SocketAddr;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "book_api=debug".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Initialize database
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db".into());
    let pool = SqlitePool::connect(&database_url).await?;

    // Run migrations
    sqlx::migrate!("./migrations").run(&pool).await?;

    // Build application
    let app = Router::new()
        .route("/health", get(handlers::health))
        .route("/books", post(handlers::create_book))
        .route("/books", get(handlers::list_books))
        .route("/books/:id", get(handlers::get_book))
        .route("/books/:id", put(handlers::update_book))
        .route("/books/:id", delete(handlers::delete_book))
        .with_state(pool);

    let addr = SocketAddr::from(([127, 0, 0, 1], with_env_port()));
    tracing::info!("Listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

fn with_env_port() -> u16 {
    std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(3000)
}