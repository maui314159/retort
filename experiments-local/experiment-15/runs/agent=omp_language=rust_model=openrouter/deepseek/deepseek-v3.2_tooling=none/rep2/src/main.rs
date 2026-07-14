use axum::Router;
use std::net::SocketAddr;
use tracing_subscriber;

use book_collection_api::routes;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    // Create database connection pool
    let pool = book_collection_api::db::create_pool().await?;

    // Build application
    let app = Router::new()
        .merge(routes::health::router())
        .merge(routes::books::router(pool));
    // Start server
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    tracing::info!("Server listening on {}", addr);
    axum::serve(tokio::net::TcpListener::bind(addr).await?, app)
        .await
        .map_err(|e| e.into())
}