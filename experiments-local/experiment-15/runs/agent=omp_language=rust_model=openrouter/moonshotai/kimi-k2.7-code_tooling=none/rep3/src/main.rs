use anyhow::Context;
use book_api::create_app;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let db_path = std::env::var("DATABASE").unwrap_or_else(|_| ":memory:".to_string());
    let port = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(3000u16);

    let app = create_app(&db_path)?;

    let listener = tokio::net::TcpListener::bind(("0.0.0.0", port))
        .await
        .context("failed to bind TCP listener")?;

    println!("Book API listening on 0.0.0.0:{port}");
    axum::serve(listener, app).await?;
    Ok(())
}
