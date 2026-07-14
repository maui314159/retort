use std::env;
use std::net::SocketAddr;

use anyhow::Context;
use book_collection_api::{build_router, db};
use tokio::net::TcpListener;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_tracing();

    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite://books.db?mode=rwc".to_string());
    let bind_addr = env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8080".to_string());

    let pool = db::init_pool(&database_url)
        .await
        .with_context(|| format!("failed to connect to database at {database_url}"))?;
    db::run_migrations(&pool)
        .await
        .context("failed to run database migrations")?;

    let app = build_router(pool);
    let addr: SocketAddr = bind_addr
        .parse()
        .with_context(|| format!("invalid BIND_ADDR: {bind_addr}"))?;
    let listener = TcpListener::bind(addr)
        .await
        .with_context(|| format!("failed to bind to {addr}"))?;

    tracing::info!("book-collection-api listening on http://{addr}");

    let server = axum::serve(listener, app);
    if let Err(err) = server.await {
        tracing::error!("server error: {err:#}");
        return Err(err).context("server stopped unexpectedly");
    }

    Ok(())
}

fn init_tracing() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,book_collection_api=debug,tower_http=info"));
    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().with_target(false))
        .init();
}
