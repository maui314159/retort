use std::env;
use std::net::SocketAddr;

use book_collection::db;
use book_collection::handlers::AppState;
use book_collection::router;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    let db_path = env::var("BOOK_DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let host = env::var("BOOK_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port: u16 = env::var("BOOK_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(3000);

    let pool = db::open_pool(&db_path)?;
    db::migrate(&pool)?;

    let addr: SocketAddr = format!("{host}:{port}").parse()?;
    tracing::info!("listening on http://{addr} (db={db_path})");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, router::app(AppState { pool })).await?;
    Ok(())
}
