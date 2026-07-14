use book_api::run_app;
use std::net::SocketAddr;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "book_api=info,tower_http=info".into()),
        )
        .init();

    let db_path =
        std::env::var("BOOKS_DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr: SocketAddr =
        std::env::var("BOOKS_ADDR")
            .unwrap_or_else(|_| "127.0.0.1:8080".to_string())
            .parse()
            .expect("valid BOOKS_ADDR");

    run_app(&db_path, addr).await?;
    Ok(())
}
