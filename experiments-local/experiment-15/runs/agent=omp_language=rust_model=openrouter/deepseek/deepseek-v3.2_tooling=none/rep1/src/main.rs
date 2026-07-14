mod error;
mod models;
mod database;
mod handlers;
use database::create_pool;
use std::net::SocketAddr;
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    tracing_subscriber::fmt::init();

    // Database URL - in production, this would come from environment variables
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite:books.db".to_string());

    let pool = create_pool(&database_url).await?;
    // Build our application with routes
    let app = handlers::create_router(pool);

    // Run server
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    tracing::info!("Server listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
