use books_api::{db, handlers};
use sqlx::sqlite::SqlitePoolOptions;
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_url =
        env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db?mode=rwc".to_string());

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&db_url)
        .await?;
    db::init(&pool).await?;

    let state = handlers::AppState { pool };
    let app = handlers::router(state);

    let addr = env::var("LISTEN_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("books-api listening on http://{addr}");
    axum::serve(listener, app).await?;
    Ok(())
}
