use book_api::app_router;
use book_api::db::Db;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let db_path = std::env::var("BOOK_DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = Db::open(&db_path)?;

    let app = app_router(db).layer(tower_http::trace::TraceLayer::new_for_http());

    let addr = std::env::var("BOOK_API_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!("listening on {addr}");
    axum::serve(listener, app).await?;
    Ok(())
}
